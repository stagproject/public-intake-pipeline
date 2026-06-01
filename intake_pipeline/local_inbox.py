"""Local folder intake: ZIP / HTML / XML → normalized staging + JSON manifest.

Optional --register writes pending rows to Supabase (intake_batch_status).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from intake_pipeline.config import REPO_ROOT
from intake_pipeline.hashing import sha256_bytes
from intake_pipeline.store import upsert_pending

INBOX = REPO_ROOT / "data" / "inbox"
WORK = REPO_ROOT / "data" / "work"
OUTBOX = REPO_ROOT / "data" / "outbox"
STAGING = REPO_ROOT / "data" / "staging"

ACCESSION_RE = re.compile(r"(\d{10})-(\d{2})-(\d{6})")
DOC_ID_RE = re.compile(r"^(\d{18})\.htm$", re.I)


def accession_to_document_id(name: str) -> str | None:
    m = ACCESSION_RE.search(name)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    stem = Path(name).stem.replace("-", "")
    if len(stem) == 18 and stem.isdigit():
        return stem
    return None


def _pick_primary_htm(files: list[Path]) -> Path | None:
    htms = [p for p in files if p.suffix.lower() in (".htm", ".html")]
    if not htms:
        return None
    for p in htms:
        if "10-k" in p.name.lower() or "10-q" in p.name.lower():
            return p
    return max(htms, key=lambda x: x.stat().st_size)


def _extract_zip(zip_path: Path, dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)
    return [p for p in dest.rglob("*") if p.is_file()]


def _xml_to_text_summary(xml_path: Path) -> str:
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        return ET.tostring(root, encoding="unicode")[:500_000]
    except ET.ParseError:
        return xml_path.read_text(encoding="utf-8", errors="replace")[:500_000]


def process_inbox(*, register: bool = False) -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    STAGING.mkdir(parents=True, exist_ok=True)

    entries = sorted(
        p for p in INBOX.iterdir() if p.is_file() and p.suffix.lower() in (".zip", ".xml", ".htm", ".html")
    )
    if not entries:
        print(f"Inbox is empty: {INBOX}")
        print("  Drop .zip / .xml / .htm files and run again.")
        return 1

    sb = None
    if register:
        from intake_pipeline.store import get_supabase

        sb = get_supabase()

    manifest_items: list[dict] = []
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    for src in entries:
        doc_id = accession_to_document_id(src.name)
        job_dir = WORK / f"{ts}_{src.stem}"
        job_dir.mkdir(parents=True, exist_ok=True)
        primary_htm: Path | None = None
        meta: dict = {"source_file": src.name, "source_type": src.suffix.lower()}

        if src.suffix.lower() == ".zip":
            extracted = _extract_zip(src, job_dir)
            files = [Path(f) for f in extracted]
            primary_htm = _pick_primary_htm(files)
            if not doc_id and primary_htm:
                doc_id = accession_to_document_id(primary_htm.name)
            meta["extracted_files"] = len(files)
        elif src.suffix.lower() in (".htm", ".html"):
            primary_htm = job_dir / src.name
            shutil.copy2(src, primary_htm)
            if not doc_id:
                doc_id = accession_to_document_id(src.name)
        else:
            xml_text = _xml_to_text_summary(src)
            (job_dir / f"{src.stem}_parsed.txt").write_text(xml_text, encoding="utf-8")
            meta["xml_chars"] = len(xml_text)
            if not doc_id:
                doc_id = accession_to_document_id(src.name)

        if not doc_id:
            doc_id = f"local_{src.stem}"[:32]
            meta["document_id_inferred"] = False
        else:
            meta["document_id_inferred"] = True

        dest = STAGING / f"{doc_id}.htm"
        if primary_htm and primary_htm.exists():
            shutil.copy2(primary_htm, dest)
            body = dest.read_bytes()
            meta["staging_path"] = str(dest.relative_to(REPO_ROOT))
            meta["content_hash"] = sha256_bytes(body)
            meta["bytes"] = len(body)
        elif src.suffix.lower() == ".xml":
            dest.write_text(f"<!-- from {src.name} -->\n", encoding="utf-8")
            meta["converted_from_xml"] = True

        archive_dest = OUTBOX / "processed" / ts / src.name
        archive_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(archive_dest))
        meta["archived_to"] = str(archive_dest.relative_to(REPO_ROOT))

        manifest_items.append({"document_id": doc_id, **meta})
        print(f"  OK {src.name} -> {doc_id}")

        if sb and register:
            upsert_pending(
                sb,
                document_id=doc_id,
                source_key="local_inbox",
                metadata=meta,
            )

    manifest_path = OUTBOX / f"ingest_manifest_{ts}.json"
    manifest = {
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "count": len(manifest_items),
        "items": manifest_items,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote manifest: {manifest_path}")
    if register and sb:
        print(f"Registered {len(manifest_items)} row(s) in intake_batch_status")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Local document inbox intake")
    parser.add_argument(
        "--register",
        action="store_true",
        help="Upsert pending rows to Supabase (requires .env)",
    )
    args = parser.parse_args()
    sys.exit(process_inbox(register=args.register))


if __name__ == "__main__":
    main()
