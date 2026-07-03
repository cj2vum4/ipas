"""Build mobile-readable study material JSON for GitHub Pages."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "study_materials.json"
ASSET_DIR = ROOT / "docs" / "material_assets"

import sys

sys.path.insert(0, str(ROOT / "src"))

from notebooklm import config  # noqa: E402
from rag.builder import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, chunk_text  # noqa: E402
from rag.loaders import discover_files, load_document  # noqa: E402


def main() -> int:
    source_paths = [ROOT / "iPAS教材", config.DATA_DIR]
    files = discover_files([path for path in source_paths if path.exists()])
    materials = []
    ready = 0
    needs_ocr = 0

    for path in files:
        relative = _relative_path(path)
        record = {
            "id": material_id(relative),
            "title": path.stem,
            "path": relative,
            "kind": path.suffix.lower().lstrip("."),
            "category": category_for(relative, path.name),
            "status": "ready",
            "reason": "",
            "assetPath": "",
            "chars": 0,
            "sections": [],
        }
        try:
            document = load_document(path, ROOT)
            sections = chunk_text(document.text, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)
            record["title"] = document.title
            record["kind"] = document.kind
            record["chars"] = len(document.text)
            record["sections"] = [
                {
                    "index": index + 1,
                    "title": f"第 {index + 1} 段",
                    "text": text,
                }
                for index, text in enumerate(sections)
            ]
            ready += 1
        except Exception as exc:
            reason = str(exc)
            record["status"] = "needs_ocr" if _needs_ocr(reason, path.suffix) else "skipped"
            record["reason"] = reason
            if record["status"] == "needs_ocr" and path.suffix.lower() in {".jpeg", ".jpg", ".pdf", ".png"}:
                record["assetPath"] = _copy_asset(path, record["id"])
            if record["status"] == "needs_ocr":
                needs_ocr += 1
        materials.append(record)

    payload = {
        "schema": "ipas-study-materials-v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceCount": len(materials),
        "readyCount": ready,
        "needsOcrCount": needs_ocr,
        "materials": materials,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {OUTPUT} with {len(materials)} materials "
        f"({ready} readable, {needs_ocr} need OCR)"
    )
    return 0


def material_id(relative_path: str) -> str:
    from hashlib import sha1

    return "src_" + sha1(relative_path.encode("utf-8")).hexdigest()[:14]


def category_for(relative: str, name: str) -> str:
    text = f"{relative} {name}".lower()
    if "l21" in text or "l211" in text or "l212" in text or "l213" in text:
        return "中級 L21"
    if "l22" in text or "l221" in text or "l222" in text or "l223" in text or "l224" in text:
        return "中級 L22"
    if "l23" in text or "l230" in text or "l231" in text or "機器學習" in text:
        return "中級 L23"
    if "考古" in text or "模擬" in text or "考題" in text or "樣題" in text or "情境" in text:
        return "考古與模擬"
    if "初級" in text or "公版" in text or "生成式" in text or "人工智慧基礎" in text:
        return "初級與基礎"
    if "data/" in relative:
        return "NotebookLM"
    return "其他"


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _needs_ocr(reason: str, suffix: str) -> bool:
    lowered = reason.lower()
    return (
        suffix.lower() in {".jpeg", ".jpg", ".pdf", ".png"}
        or "ocr" in lowered
        or "no extractable text" in lowered
    )


def _copy_asset(path: Path, material_id_value: str) -> str:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("_")[:48] or "asset"
    filename = f"{material_id_value}__{safe_title}{suffix}"
    target = ASSET_DIR / filename
    shutil.copy2(path, target)
    return f"material_assets/{filename}"


if __name__ == "__main__":
    raise SystemExit(main())
