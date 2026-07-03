"""Document readers for local iPAS material and NotebookLM exports."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

SUPPORTED_EXTENSIONS = {
    ".docx",
    ".jpeg",
    ".jpg",
    ".json",
    ".md",
    ".pdf",
    ".png",
    ".txt",
    ".xlsx",
}

_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


class LoaderError(RuntimeError):
    """Raised when a file is recognised but cannot be read as text."""


@dataclass
class Document:
    source_id: str
    path: str
    title: str
    kind: str
    text: str


@dataclass
class LoadIssue:
    path: str
    reason: str


def discover_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            candidates = [path]
        else:
            candidates = [candidate for candidate in path.rglob("*") if candidate.is_file()]
        for candidate in candidates:
            if candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(candidate)
    return sorted(dict.fromkeys(files), key=lambda item: str(item).lower())


def load_document(path: Path, project_root: Path) -> Document:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        text = _read_text(path)
    elif suffix == ".docx":
        text = _read_docx(path)
    elif suffix == ".xlsx":
        text = _read_xlsx(path)
    elif suffix == ".pdf":
        text = _read_pdf(path)
    elif suffix == ".json":
        text = _read_notebook_json(path)
    elif suffix in {".jpeg", ".jpg", ".png"}:
        raise LoaderError("image file requires OCR or manual notes")
    else:
        raise LoaderError(f"unsupported extension: {suffix}")

    text = _clean_text(text)
    if not text:
        raise LoaderError("no extractable text")

    relative = _relative_path(path, project_root)
    return Document(
        source_id=_source_id(relative),
        path=relative,
        title=path.stem,
        kind=suffix.lstrip("."),
        text=text,
    )


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _source_id(relative_path: str) -> str:
    from hashlib import sha1

    return "src_" + sha1(relative_path.encode("utf-8")).hexdigest()[:14]


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp950", "big5", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise LoaderError("unknown text encoding")


def _read_docx(path: Path) -> str:
    parts = [
        "word/document.xml",
        "word/footnotes.xml",
        "word/endnotes.xml",
    ]
    paragraphs: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            for part in parts:
                if part not in archive.namelist():
                    continue
                root = ElementTree.fromstring(archive.read(part))
                for para in root.iter(f"{_WORD_NS}p"):
                    texts = [
                        node.text or ""
                        for node in para.iter(f"{_WORD_NS}t")
                        if node.text
                    ]
                    line = "".join(texts).strip()
                    if line:
                        paragraphs.append(line)
    except (ElementTree.ParseError, KeyError, zipfile.BadZipFile) as exc:
        raise LoaderError(f"invalid docx: {exc}") from exc
    return "\n".join(paragraphs)


def _read_xlsx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            shared = _read_shared_strings(archive)
            sheet_names = sorted(
                name
                for name in archive.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            )
            lines: list[str] = []
            for sheet_name in sheet_names:
                root = ElementTree.fromstring(archive.read(sheet_name))
                lines.append(f"## {Path(sheet_name).stem}")
                for row in root.iter(f"{_SHEET_NS}row"):
                    values = [
                        _cell_value(cell, shared)
                        for cell in row.iter(f"{_SHEET_NS}c")
                    ]
                    values = [value for value in values if value]
                    if values:
                        lines.append("\t".join(values))
    except (ElementTree.ParseError, KeyError, zipfile.BadZipFile) as exc:
        raise LoaderError(f"invalid xlsx: {exc}") from exc
    return "\n".join(lines)


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.iter(f"{_SHEET_NS}si"):
        strings.append("".join(node.text or "" for node in item.iter(f"{_SHEET_NS}t")))
    return strings


def _cell_value(cell: ElementTree.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{_SHEET_NS}t")).strip()

    value = cell.find(f"{_SHEET_NS}v")
    if value is None or value.text is None:
        return ""
    raw = value.text.strip()
    if cell_type == "s":
        try:
            return shared[int(raw)].strip()
        except (IndexError, ValueError):
            return raw
    return raw


def _read_pdf(path: Path) -> str:
    pypdf_text = _read_pdf_with_python_package(path)
    if pypdf_text:
        return pypdf_text
    if _pdf_parser_available():
        raise LoaderError("no extractable text; likely scanned PDF/OCR required")

    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        try:
            result = subprocess.run(
                [pdftotext, "-layout", str(path), "-"],
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise LoaderError(f"pdftotext failed: {exc}") from exc
        return result.stdout

    raise LoaderError("PDF support requires pypdf/PyPDF2 or pdftotext")


def _pdf_parser_available() -> bool:
    try:
        import pypdf  # noqa: F401

        return True
    except ImportError:
        try:
            import PyPDF2  # noqa: F401

            return True
        except ImportError:
            return False


def _read_pdf_with_python_package(path: Path) -> str:
    reader_class = None
    try:
        from pypdf import PdfReader  # type: ignore

        reader_class = PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore

            reader_class = PdfReader
        except ImportError:
            return ""

    try:
        reader = reader_class(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:  # pragma: no cover - depends on third-party parser
        raise LoaderError(f"PDF parser failed: {exc}") from exc


def _read_notebook_json(path: Path) -> str:
    try:
        payload = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        raise LoaderError(f"invalid json: {exc}") from exc

    if isinstance(payload, dict) and (
        "summary" in payload or "sources" in payload or "notes" in payload
    ):
        sections: list[str] = []
        title = str(payload.get("title") or path.stem).strip()
        if title:
            sections.append(f"# {title}")
        if payload.get("summary"):
            sections.append(str(payload["summary"]))
        for source in payload.get("sources") or []:
            if not isinstance(source, dict):
                continue
            source_text = "\n".join(
                str(source.get(key) or "")
                for key in ("title", "kind", "preview")
                if source.get(key)
            ).strip()
            if source_text:
                sections.append(source_text)
        for note in payload.get("notes") or []:
            if not isinstance(note, dict):
                continue
            note_text = "\n".join(
                str(note.get(key) or "")
                for key in ("title", "content")
                if note.get(key)
            ).strip()
            if note_text:
                sections.append(note_text)
        return "\n\n".join(sections)

    raise LoaderError("not a NotebookLM export")


def _clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
