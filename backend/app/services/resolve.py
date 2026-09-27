"""
resolve.py — resolves every RawImport (from parse_py.py's RawParsedFile
objects) to a repo file, external package, or unresolved, and builds the
final schema.ParsedFile / schema.ImportRef objects. Never guesses: anything
ambiguous, external, or dynamic is marked accordingly rather than being
force-matched.

Locked spec constraints honored here:
- Unresolved imports → an explicit UnresolvedBucket, never guessed.
- POSIX paths everywhere.
- Handles relative imports (`from . import x`, `from ..pkg import y`),
  package `__init__.py` re-exports, and absolute-within-repo imports.
- schema.ImportRef.status distinguishes "external" (resolved to a known
  third-party/stdlib package — not an error) from "unresolved" (looked
  internal but couldn't be matched to any repo file — the real ambiguous
  case). Only "unresolved" entries go into UnresolvedBucket.

Public API:
    resolve_all(raw_files: list[RawParsedFile]) -> tuple[list[ParsedFile], UnresolvedBucket]
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Optional

from ..schema import ImportRef, ImportResolutionStatus, ParsedFile, UnresolvedBucket
from .parse_py import RawParsedFile


def _build_module_index(raw_files: list) -> dict:
    """dotted-module-path -> repo-relative file path, for every parsed file."""
    index = {}
    for rf in raw_files:
        parts = list(PurePosixPath(rf.path).parts)
        if not parts or not parts[-1].endswith(".py"):
            continue
        stem = parts[-1][:-3]
        dotted = ".".join(parts[:-1]) if stem == "__init__" else ".".join(parts[:-1] + [stem])
        if dotted:
            index[dotted] = rf.path
    return index


def _resolve_relative(source_path: str, imp, module_index: dict) -> Optional[str]:
    source_parts = list(PurePosixPath(source_path).parts)
    if not source_parts:
        return None
    dir_parts = source_parts[:-1]
    climb = imp.level - 1
    if climb > 0:
        if climb > len(dir_parts):
            return None
        dir_parts = dir_parts[: len(dir_parts) - climb]

    target_parts = list(dir_parts)
    if imp.module:
        target_parts += imp.module.split(".")
    dotted = ".".join(target_parts)
    if dotted in module_index:
        return module_index[dotted]

    if not imp.module:
        for name in imp.names:
            candidate = ".".join(dir_parts + [name])
            if candidate in module_index:
                return module_index[candidate]
    return None


def _looks_internal(module: str, module_index: dict) -> bool:
    if not module:
        return False
    top = module.split(".")[0]
    return any(dotted == top or dotted.startswith(top + ".") for dotted in module_index)


def _resolve_absolute(imp, module_index: dict) -> Optional[str]:
    if imp.module in module_index:
        return module_index[imp.module]
    parts = imp.module.split(".") if imp.module else []
    for cut in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:cut])
        if prefix in module_index:
            return module_index[prefix]
    return None


def _finalize_import(source_path: str, imp, module_index: dict) -> ImportRef:
    if imp.is_relative:
        target = _resolve_relative(source_path, imp, module_index)
        status = ImportResolutionStatus.resolved if target else ImportResolutionStatus.unresolved
    else:
        target = _resolve_absolute(imp, module_index)
        if target:
            status = ImportResolutionStatus.resolved
        elif _looks_internal(imp.module, module_index):
            status = ImportResolutionStatus.unresolved
        else:
            status = ImportResolutionStatus.external

    return ImportRef(
        raw=imp.raw,
        module=imp.module or ".",
        line=imp.line,
        status=status,
        resolved_path=target if status == ImportResolutionStatus.resolved else None,
    )


def resolve_all(raw_files: list) -> tuple:
    """
    Resolves every import across the whole repo and returns
    (final_parsed_files, unresolved_bucket).
    """
    module_index = _build_module_index(raw_files)
    final_files = []
    unresolved_imports = []

    for rf in raw_files:
        final_imports = []
        for imp in rf.raw_imports:
            resolved_ref = _finalize_import(rf.path, imp, module_index)
            final_imports.append(resolved_ref)
            if resolved_ref.status == ImportResolutionStatus.unresolved:
                unresolved_imports.append(resolved_ref)

        final_files.append(ParsedFile(
            path=rf.path,
            language=rf.language,
            line_count=rf.line_count,
            docstring=rf.docstring,
            imports=final_imports,
            symbols=rf.symbols,
            parse_error=rf.parse_error,
        ))

    return final_files, UnresolvedBucket(imports=unresolved_imports)
