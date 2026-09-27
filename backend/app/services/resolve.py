"""
resolve.py — resolves ImportRef entries (produced by parse_py.py) across all
parsed files in a repo to an actual file within the repo, or files them into
the "unresolved" bucket. Never guesses: anything ambiguous, external, or
dynamic goes to unresolved rather than being force-matched.

Locked spec constraints honored here:
- Unresolved imports → "unresolved" bucket, never guessed.
- POSIX paths everywhere.
- Handles: relative imports (`from . import x`, `from ..pkg import y`),
  package `__init__.py` re-exports, and absolute-within-repo imports
  (`import mypkg.module`).
- External/stdlib packages are NOT treated as errors — they're expected
  and go to unresolved with reason "external_or_stdlib", distinct from
  imports that looked internal but couldn't be found
  ("not_found_in_repo") or were too dynamic to resolve ("dynamic").

Public API:
    resolve_imports(parsed_files: list[ParsedFile]) -> ResolveResult
        where ResolveResult has:
            resolved: list[ResolvedImport]   (import -> file:line)
            unresolved: list[UnresolvedEntry]
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Optional

try:
    from ..schema import ImportRef, ParsedFile, UnresolvedBucket
except ImportError:  # pragma: no cover - standalone/local testing fallback only
    from dataclasses import dataclass, field

    @dataclass
    class ImportRef:
        module: str
        names: list
        is_relative: bool
        level: int
        line: int

    @dataclass
    class ParsedFile:
        path: str
        imports: list = field(default_factory=list)

    @dataclass
    class UnresolvedBucket:
        source_file: str
        import_line: int
        module: str
        reason: str


class ResolvedImport:
    """Not a schema.py model on its own — resolved imports are attached
    back onto edges downstream (Y4/group.py consumes these), so this is a
    plain internal container: source file -> target file:line."""

    __slots__ = ("source_file", "import_line", "module", "target_file", "target_line")

    def __init__(self, source_file: str, import_line: int, module: str,
                 target_file: str, target_line: int = 1):
        self.source_file = source_file
        self.import_line = import_line
        self.module = module
        self.target_file = target_file
        self.target_line = target_line

    def __repr__(self):
        return (f"ResolvedImport({self.source_file}:{self.import_line} "
                f"-> {self.target_file}:{self.target_line}, module={self.module!r})")


class ResolveResult:
    __slots__ = ("resolved", "unresolved")

    def __init__(self, resolved: list, unresolved: list):
        self.resolved = resolved
        self.unresolved = unresolved


def _build_module_index(parsed_files: list) -> dict:
    """
    Build a lookup of dotted-module-path -> repo-relative file path, for
    every parsed file, so absolute-within-repo imports can be matched.

    Rules:
        pkg/sub/mod.py       -> "pkg.sub.mod"
        pkg/sub/__init__.py  -> "pkg.sub"        (package re-export target)
    Root-level files (no directory) map directly: "mod.py" -> "mod".
    """
    index = {}
    for pf in parsed_files:
        posix_path = PurePosixPath(pf.path)
        parts = list(posix_path.parts)
        if not parts or not parts[-1].endswith(".py"):
            continue
        stem = parts[-1][:-3]  # strip ".py"
        if stem == "__init__":
            dotted = ".".join(parts[:-1])
        else:
            dotted = ".".join(parts[:-1] + [stem])
        if dotted:  # skip pathological empty case
            index[dotted] = pf.path
    return index


def _resolve_relative(source_path: str, imp, module_index: dict) -> Optional[str]:
    """
    Resolve a relative import (level >= 1) to a repo-relative file path.
    `from . import x`        (level=1, module="")   -> sibling package/module
    `from .sibling import y` (level=1, module="sibling")
    `from ..pkg import z`    (level=2, module="pkg")
    """
    source_parts = list(PurePosixPath(source_path).parts)
    if not source_parts:
        return None
    # Directory containing the source file.
    dir_parts = source_parts[:-1]
    # level=1 means "current package" (the dir the file lives in).
    # Each extra level walks up one more package.
    climb = imp.level - 1
    if climb > 0:
        if climb > len(dir_parts):
            return None  # climbing above repo root — can't resolve
        dir_parts = dir_parts[: len(dir_parts) - climb]

    target_parts = list(dir_parts)
    if imp.module:
        target_parts += imp.module.split(".")

    dotted = ".".join(target_parts)
    if dotted in module_index:
        return module_index[dotted]

    # `from . import x` style: module is "" and the real target is one of
    # the imported names as a submodule of the current package.
    if not imp.module:
        for name in imp.names:
            candidate_dotted = ".".join(dir_parts + [name])
            if candidate_dotted in module_index:
                return module_index[candidate_dotted]

    return None


def _looks_internal(module: str, module_index: dict) -> bool:
    """Heuristic: an absolute import is worth trying to resolve internally
    only if its top-level component could plausibly be a repo package
    (i.e. some indexed module starts with that same top-level name)."""
    if not module:
        return False
    top = module.split(".")[0]
    return any(dotted == top or dotted.startswith(top + ".") for dotted in module_index)


def resolve_imports(parsed_files: list) -> ResolveResult:
    module_index = _build_module_index(parsed_files)
    resolved: list = []
    unresolved: list = []

    for pf in parsed_files:
        for imp in getattr(pf, "imports", []):
            if imp.is_relative:
                target = _resolve_relative(pf.path, imp, module_index)
                if target:
                    resolved.append(
                        ResolvedImport(pf.path, imp.line, imp.module or ".", target)
                    )
                else:
                    unresolved.append(
                        UnresolvedBucket(
                            source_file=pf.path,
                            import_line=imp.line,
                            module=imp.module or ".",
                            reason="not_found_in_repo",
                        )
                    )
                continue

            # Absolute import.
            if imp.module in module_index:
                resolved.append(
                    ResolvedImport(pf.path, imp.line, imp.module, module_index[imp.module])
                )
                continue

            # Try progressively shorter dotted prefixes in case it's a
            # `from pkg.mod import name` where `pkg.mod` is a package and
            # `name` is an attribute/re-export rather than a submodule.
            parts = imp.module.split(".") if imp.module else []
            matched = None
            for cut in range(len(parts) - 1, 0, -1):
                prefix = ".".join(parts[:cut])
                if prefix in module_index:
                    matched = module_index[prefix]
                    break

            if matched:
                resolved.append(ResolvedImport(pf.path, imp.line, imp.module, matched))
            elif _looks_internal(imp.module, module_index):
                unresolved.append(
                    UnresolvedBucket(
                        source_file=pf.path,
                        import_line=imp.line,
                        module=imp.module,
                        reason="not_found_in_repo",
                    )
                )
            else:
                unresolved.append(
                    UnresolvedBucket(
                        source_file=pf.path,
                        import_line=imp.line,
                        module=imp.module,
                        reason="external_or_stdlib",
                    )
                )

    return ResolveResult(resolved=resolved, unresolved=unresolved)
