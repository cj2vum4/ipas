#!/usr/bin/env python3
"""CLI for extracting data out of Google NotebookLM.

NotebookLM has no public API, so this tool drives a signed-in Chromium session
with Playwright. Typical flow:

    python main.py login                 # one-time: sign in, saves session
    python main.py list                  # discover notebook ids
    python main.py extract <notebook_id> # pull one notebook -> data/*.json
    python main.py extract-all           # pull every notebook you can see

Run `python main.py <command> -h` for per-command options.
"""
from __future__ import annotations

import argparse
import json
import sys

# Allow running as `python main.py` without installing the package.
sys.path.insert(0, "src")

from notebooklm import config  # noqa: E402
from rag import builder as rag_builder  # noqa: E402


def _add_headless_flag(p: argparse.ArgumentParser) -> None:
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        default=None,
        help="Force headless browser (default for extraction).",
    )
    group.add_argument(
        "--headed",
        dest="headless",
        action="store_false",
        help="Show the browser window (useful for debugging).",
    )


def cmd_login(args: argparse.Namespace) -> int:
    from notebooklm import auth

    auth.login()
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    from notebooklm import extractor, storage

    refs = extractor.list_notebooks(headless=args.headless)
    if not refs:
        print("No notebooks found. If you expected some, run `login` again.")
        return 1
    print(f"Found {len(refs)} notebook(s):\n")
    for r in refs:
        print(f"  {r.id}  {r.title or '(untitled)'}")
    storage.save_index([r.to_dict() for r in refs])
    print(f"\nIndex written to {config.DATA_DIR / 'notebooks_index.json'}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    from notebooklm import extractor, storage

    nb = extractor.extract_notebook(args.notebook_id, headless=args.headless)
    out = storage.save_notebook(nb)
    print(
        f"Extracted '{nb.title or nb.id}': "
        f"{len(nb.sources)} source(s), {len(nb.notes)} note(s)."
    )
    print(f"Saved -> {out}")
    return 0


def cmd_extract_all(args: argparse.Namespace) -> int:
    from notebooklm import extractor, storage

    refs = extractor.list_notebooks(headless=args.headless)
    if not refs:
        print("No notebooks found.")
        return 1
    index = []
    for r in refs:
        print(f"Extracting {r.id} ({r.title or 'untitled'})...")
        nb = extractor.extract_notebook(r.id, headless=args.headless)
        out = storage.save_notebook(nb)
        index.append(r.to_dict())
        print(f"  -> {out}")
    storage.save_index(index)
    print(f"\nDone. {len(refs)} notebook(s) saved to {config.DATA_DIR}")
    return 0


def cmd_debug_dump(args: argparse.Namespace) -> int:
    from notebooklm import extractor

    text = extractor.debug_dump(args.notebook_id, headless=args.headless)
    print(text)
    return 0


def cmd_rag_build(args: argparse.Namespace) -> int:
    source_paths = (
        [config.PROJECT_ROOT / path for path in args.paths]
        if args.paths
        else rag_builder.default_source_paths()
    )
    output_path = config.PROJECT_ROOT / args.output
    stats = rag_builder.build_index(
        source_paths,
        output_path=output_path,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_chunks=args.max_chunks,
    )

    print(f"Files scanned: {stats.files_seen}")
    print(f"Sources indexed: {stats.sources}")
    print(f"Chunks indexed: {stats.chunks}")
    print(f"Index written to: {stats.output_path}")

    if stats.skipped:
        print(f"\nSkipped {len(stats.skipped)} file(s):")
        for issue in stats.skipped[:20]:
            print(f"  - {issue.path}: {issue.reason}")
        if len(stats.skipped) > 20:
            print(f"  ... and {len(stats.skipped) - 20} more")

    return 0 if stats.chunks else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notebooklm",
        description="Extract data from Google NotebookLM (browser automation).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_login = sub.add_parser("login", help="Interactive sign-in; saves session.")
    p_login.set_defaults(func=cmd_login)

    p_list = sub.add_parser("list", help="List visible notebooks.")
    _add_headless_flag(p_list)
    p_list.set_defaults(func=cmd_list)

    p_extract = sub.add_parser("extract", help="Extract one notebook by id.")
    p_extract.add_argument("notebook_id", help="Notebook id (see `list`).")
    _add_headless_flag(p_extract)
    p_extract.set_defaults(func=cmd_extract)

    p_all = sub.add_parser("extract-all", help="Extract every visible notebook.")
    _add_headless_flag(p_all)
    p_all.set_defaults(func=cmd_extract_all)

    p_dump = sub.add_parser(
        "debug-dump", help="Print rendered page text to refresh selectors."
    )
    p_dump.add_argument(
        "notebook_id", nargs="?", default=None, help="Optional notebook id."
    )
    _add_headless_flag(p_dump)
    p_dump.set_defaults(func=cmd_debug_dump)

    p_rag = sub.add_parser(
        "rag-build",
        help="Build docs/rag_index.json for the static RAG web app.",
    )
    p_rag.add_argument(
        "paths",
        nargs="*",
        help="Files or folders to index. Defaults to iPAS教材 and data.",
    )
    p_rag.add_argument(
        "-o",
        "--output",
        default="docs/rag_index.json",
        help="Output JSON path relative to the project root.",
    )
    p_rag.add_argument(
        "--chunk-size",
        type=int,
        default=rag_builder.DEFAULT_CHUNK_SIZE,
        help="Approximate chunk size in characters.",
    )
    p_rag.add_argument(
        "--chunk-overlap",
        type=int,
        default=rag_builder.DEFAULT_CHUNK_OVERLAP,
        help="Characters to overlap between adjacent chunks.",
    )
    p_rag.add_argument(
        "--max-chunks",
        type=int,
        default=0,
        help="Stop after this many chunks (0 means no limit).",
    )
    p_rag.set_defaults(func=cmd_rag_build)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
