"""SEC EDGAR example collector — lawful public API access with rate limits.

Demonstrates:
- Required User-Agent header
- Skip-if-exists (idempotent) status rows in Supabase
- Optional raw artifact upload to S3-compatible storage
- RSS-based discovery for monitored CIKs

Not a full production EDGAR mirror; see --mode TEST for a single-document demo.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import boto3
import requests
from botocore.config import Config
from dotenv import load_dotenv

from intake_pipeline.config import REPO_ROOT, load_config
from intake_pipeline.hashing import sha256_bytes
from intake_pipeline.store import (
    TABLE_WATCHLIST,
    document_exists,
    get_supabase,
    upsert_pending,
)

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _headers() -> dict[str, str]:
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        raise ValueError(
            "SEC_USER_AGENT is required in .env (see https://www.sec.gov/os/webmaster-faq#code-support)"
        )
    return {"User-Agent": ua}


def _object_storage_client():
    endpoint = os.environ.get("OBJECT_STORAGE_ENDPOINT_URL", "").strip()
    if not endpoint:
        return None, None
    bucket = os.environ.get("OBJECT_STORAGE_BUCKET", "").strip()
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("OBJECT_STORAGE_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("OBJECT_STORAGE_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    return client, bucket


def _upload_raw(client, bucket: str, document_id: str, body: bytes) -> str:
    key = f"raw/pending/{document_id}.htm"
    client.put_object(Bucket=bucket, Key=key, Body=body)
    return key


def run_test_mode(delay: float) -> int:
    """Download one well-known public filing (Apple 10-K sample path) for demos."""
    load_dotenv(REPO_ROOT / ".env")
    headers = _headers()
    cik = "0000320193"
    # Public index page (no authentication)
    index_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K&count=1"
    time.sleep(delay)
    res = requests.get(index_url, headers=headers, timeout=30)
    res.raise_for_status()
    print(f"SEC index reachable ({res.status_code}). Configure Supabase to persist records.")
    print(f"Example index URL: {index_url}")
    return 0


def run_daily_mode(delay: float, max_new: int) -> int:
    load_dotenv(REPO_ROOT / ".env")
    headers = _headers()
    cfg = load_config()
    sb = get_supabase()
    s3, bucket = _object_storage_client()

    res = sb.table(TABLE_WATCHLIST).select("cik, label").eq("is_active", True).execute()
    watch = {row["cik"]: row.get("label") or row["cik"] for row in (res.data or [])}
    if not watch:
        print("No rows in intake_watchlist with is_active=true. Add CIKs in Supabase first.")
        return 1

    rss_urls = [
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=10-K&count=40&output=atom",
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=10-Q&count=40&output=atom",
    ]
    tasks: list[dict[str, str]] = []
    for rss_url in rss_urls:
        time.sleep(delay)
        rss_res = requests.get(rss_url, headers=headers, timeout=30)
        if rss_res.status_code != 200:
            continue
        root = ET.fromstring(rss_res.content)
        for entry in root.findall("atom:entry", ATOM_NS):
            title_el = entry.find("atom:title", ATOM_NS)
            if title_el is None or not title_el.text:
                continue
            cik_match = re.search(r"\((\d{10})\)", title_el.text)
            if not cik_match:
                continue
            cik = cik_match.group(1)
            if cik not in watch:
                continue
            link_el = entry.find("atom:link", ATOM_NS)
            if link_el is None:
                continue
            acc_match = re.search(r"/(\d{10}-?\d{2}-?\d{6})", link_el.attrib.get("href", ""))
            if not acc_match:
                continue
            acc_no = acc_match.group(1).replace("-", "")
            tasks.append({"cik": cik, "document_id": acc_no, "label": watch[cik]})

    saved = 0
    for task in tasks:
        if saved >= max_new:
            break
        doc_id = task["document_id"]
        if document_exists(sb, doc_id):
            continue

        time.sleep(delay)
        cik = task["cik"]
        sub_res = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers, timeout=30)
        if sub_res.status_code != 200:
            continue
        filings = sub_res.json().get("filings", {}).get("recent", {})
        idx = -1
        for i, a in enumerate(filings.get("accessionNumber", [])):
            if a.replace("-", "") == doc_id:
                idx = i
                break
        if idx == -1:
            continue
        form = filings["form"][idx]
        if form not in ("10-K", "10-Q"):
            continue
        primary = filings["primaryDocument"][idx]
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{doc_id}/{primary}"
        time.sleep(delay)
        doc_res = requests.get(doc_url, headers=headers, timeout=60)
        if doc_res.status_code != 200:
            continue

        content_hash = sha256_bytes(doc_res.content)
        storage_path = None
        if s3 and bucket:
            storage_path = _upload_raw(s3, bucket, doc_id, doc_res.content)

        upsert_pending(
            sb,
            document_id=doc_id,
            source_key="sec_edgar",
            metadata={
                "cik": cik,
                "form_type": form,
                "filed_date": filings["filingDate"][idx],
                "source_url": doc_url,
                "content_hash": content_hash,
                "storage_path": storage_path,
            },
        )
        print(f"Saved pending: {task['label']} {form} {doc_id}")
        saved += 1

    print(f"Done. New records: {saved}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SEC EDGAR public intake example")
    parser.add_argument("--mode", choices=("TEST", "DAILY"), default="TEST")
    parser.add_argument("--max-new", type=int, default=5, help="DAILY mode: cap new rows per run")
    args = parser.parse_args()
    cfg = load_config()
    delay = float(cfg["SEC_API_DELAY"])

    if args.mode == "TEST":
        return run_test_mode(delay)
    return run_daily_mode(delay, args.max_new)


if __name__ == "__main__":
    sys.exit(main())
