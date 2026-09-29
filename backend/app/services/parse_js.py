from __future__ import annotations
import posixpath, re
from pathlib import Path
from typing import Optional
from app.schema import ImportRef, ImportResolutionStatus, Language, ParsedFile, SymbolRef
from app.services.scan import ScannedFile

CODE_EXTS = (".ts", ".tsx", ".js", ".jsx")
INDEX_FILES = tuple(f"index{e}" for e in CODE_EXTS)
ASSET_EXTS = {".css", ".scss", ".sass", ".less", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".json", ".md", ".mdx", ".html", ".txt", ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4", ".wasm"}

def is_asset_specifier(spec: str) -> bool:
    return posixpath.splitext(spec)[1].lower() in ASSET_EXTS

def resolve_specifier(spec: str, importer_path: str, known_paths: set[str]) -> tuple[ImportResolutionStatus, Optional[str]]:
    is_relative = spec in (".", "..") or spec.startswith("./") or spec.startswith("../")
    if not is_relative:
        if spec.startswith(("@/", "~/", "#")):
            return ImportResolutionStatus.unresolved, None
        return ImportResolutionStatus.external, None
    target = posixpath.normpath(posixpath.join(posixpath.dirname(importer_path), spec))
    if target == ".." or target.startswith("../"):
        return ImportResolutionStatus.unresolved, None
    candidates = [target]
    stem, ext = posixpath.splitext(target)
    if ext in (".js", ".jsx"):
        candidates += [stem + ".ts", stem + ".tsx"]
    candidates += [target + e for e in CODE_EXTS]
    candidates += [posixpath.normpath(posixpath.join(target, i)) for i in INDEX_FILES]
    for c in candidates:
        if c in known_paths:
            return ImportResolutionStatus.resolved, c
    return ImportResolutionStatus.unresolved, None

def extract_file_docstring(source: str) -> Optional[str]:
    return None  # TODO

def extract_imports(source: str) -> list[tuple[str, str, int]]:
    return []  # TODO

def extract_symbols(source: str) -> list[SymbolRef]:
    return []  # TODO

def _parse_one(path: str, language: Language, source: str, known_paths: set[str]) -> ParsedFile:
    imports = []
    for raw, spec, line in extract_imports(source):
        if is_asset_specifier(spec):
            continue
        status, resolved = resolve_specifier(spec, path, known_paths)
        imports.append(ImportRef(raw=raw, module=spec, line=max(line, 1), status=status, resolved_path=resolved))
    return ParsedFile(path=path, language=language, line_count=len(source.splitlines()), docstring=extract_file_docstring(source), imports=imports, symbols=extract_symbols(source))

def parse_js_files(scanned_files: list[ScannedFile]) -> list[ParsedFile]:
    js_files = [f for f in scanned_files if f.language in ("javascript", "typescript")]
    known_paths = {f.path for f in js_files}
    out = []
    for f in js_files:
        language = Language.typescript if f.language == "typescript" else Language.javascript
        try:
            source = Path(f.absolute_path).read_text(encoding="utf-8", errors="replace")
            out.append(_parse_one(f.path, language, source, known_paths))
        except Exception as exc:
            out.append(ParsedFile(path=f.path, language=language, line_count=0, parse_error=f"{type(exc).__name__}: {exc}"))
    return out