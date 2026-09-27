"""
parse_py.py — AST-based parser for a single Python source file.

IMPORTANT: schema.py's ImportRef requires `status` (resolved/unresolved/
external) and `resolved_path` at construction time — but resolution needs
the full repo's file listing, which isn't available while parsing one file
in isolation. So this module does NOT construct final ImportRef objects.
It returns a RawParsedFile — an internal (non-pydantic) intermediate type
carrying everything needed for resolution — and resolve.py is responsible
for building the final schema.ParsedFile (with fully-resolved ImportRef
objects) once it has seen every file in the repo.

Locked spec constraints honored here:
- Python parsed with stdlib `ast` only.
- Must NEVER crash the overall scan on a bad file: syntax errors / decode
  errors are caught and the file is marked unparseable (parse_error set),
  imports/symbols left empty, instead of raising.
- POSIX paths everywhere.
- Routes are NOT a separate ParsedFile field (schema.py has none) — a
  detected route decorator produces an additional SymbolRef with
  kind="route", route_path, route_methods, alongside the normal
  kind="function" SymbolRef for the same def.
- Only top-level (module-level) functions/classes become symbols — no
  recursion into class bodies — since schema.SymbolRef.kind has no
  "method" variant.

Public API:
    parse_python_file(abs_path: Path, repo_root: Path) -> RawParsedFile
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..schema import Language, SymbolRef

_ROUTE_DECORATOR_METHODS = {
    "get", "post", "put", "patch", "delete", "options", "head", "route",
}


@dataclass
class RawImport:
    """Everything needed to resolve one import statement later, plus the
    exact fields schema.ImportRef will eventually need (raw, module, line)."""
    raw: str
    module: str          # dotted module/package; "" for bare `from . import x`
    line: int
    is_relative: bool
    level: int            # 0 for absolute; 1+ for relative
    names: list           # imported names, e.g. ["x", "y"] for `from m import x, y`


@dataclass
class RawParsedFile:
    """Intermediate parse result. resolve.py turns this into a final
    schema.ParsedFile once import resolution is complete."""
    path: str
    language: Language
    line_count: int
    docstring: Optional[str]
    symbols: list          # list[schema.SymbolRef] — already final, no resolution needed
    parse_error: Optional[str]
    raw_imports: list = field(default_factory=list)  # list[RawImport]


def _to_posix_rel(abs_path: Path, repo_root: Path) -> str:
    try:
        rel = abs_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        rel = Path(abs_path.name)
    return rel.as_posix()


def _reconstruct_raw(source: str, node: ast.AST) -> str:
    """Best-effort exact source text for an import statement. Falls back
    to a synthesized equivalent if the source segment can't be extracted
    (e.g. some odd multi-line edge cases)."""
    segment = ast.get_source_segment(source, node)
    if segment:
        return segment
    if isinstance(node, ast.Import):
        return "import " + ", ".join(a.name for a in node.names)
    if isinstance(node, ast.ImportFrom):
        dots = "." * node.level
        return f"from {dots}{node.module or ''} import " + ", ".join(a.name for a in node.names)
    return ""


def _collect_raw_imports(tree: ast.Module, source: str) -> list:
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(RawImport(
                    raw=_reconstruct_raw(source, node),
                    module=alias.name,
                    line=node.lineno,
                    is_relative=False,
                    level=0,
                    names=[],
                ))
        elif isinstance(node, ast.ImportFrom):
            imports.append(RawImport(
                raw=_reconstruct_raw(source, node),
                module=node.module or "",
                line=node.lineno,
                is_relative=node.level > 0,
                level=node.level,
                names=[a.name for a in node.names],
            ))
    return imports


def _decorator_route_info(dec: ast.expr):
    """Returns (route_path, route_methods) or None if this decorator isn't
    a recognizable HTTP route registration."""
    if not isinstance(dec, ast.Call):
        return None
    func = dec.func
    method_name = func.attr if isinstance(func, ast.Attribute) else (
        func.id if isinstance(func, ast.Name) else None
    )
    if method_name not in _ROUTE_DECORATOR_METHODS:
        return None
    if not dec.args or not isinstance(dec.args[0], ast.Constant) or not isinstance(dec.args[0].value, str):
        return None
    route_path = dec.args[0].value

    if method_name == "route":
        methods = ["GET"]
        for kw in dec.keywords:
            if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                methods = [
                    elt.value for elt in kw.value.elts
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                ] or ["GET"]
        return route_path, methods

    return route_path, [method_name.upper()]


def _collect_symbols(tree: ast.Module) -> list:
    """Top-level functions/classes only — schema.SymbolRef.kind has no
    'method' variant, so class bodies are not recursed into."""
    symbols = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(SymbolRef(
                name=node.name,
                kind="function",
                line=node.lineno,
                docstring=ast.get_docstring(node),
            ))
            for dec in node.decorator_list:
                info = _decorator_route_info(dec)
                if info:
                    route_path, route_methods = info
                    symbols.append(SymbolRef(
                        name=node.name,
                        kind="route",
                        line=node.lineno,
                        docstring=ast.get_docstring(node),
                        route_path=route_path,
                        route_methods=route_methods,
                    ))
        elif isinstance(node, ast.ClassDef):
            symbols.append(SymbolRef(
                name=node.name,
                kind="class",
                line=node.lineno,
                docstring=ast.get_docstring(node),
            ))
    return symbols


def parse_python_file(abs_path: Path, repo_root: Path) -> RawParsedFile:
    """Never raises: any failure produces a RawParsedFile with parse_error
    set and everything else empty, so the caller can keep scanning."""
    rel_path = _to_posix_rel(abs_path, repo_root)

    try:
        source = abs_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return RawParsedFile(
            path=rel_path, language=Language.python, line_count=0,
            docstring=None, symbols=[], parse_error=f"read_error: {exc}",
            raw_imports=[],
        )

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError as exc:
        return RawParsedFile(
            path=rel_path, language=Language.python,
            line_count=len(source.splitlines()), docstring=None, symbols=[],
            parse_error=f"syntax_error: line {exc.lineno}: {exc.msg}",
            raw_imports=[],
        )

    return RawParsedFile(
        path=rel_path,
        language=Language.python,
        line_count=len(source.splitlines()),
        docstring=ast.get_docstring(tree),
        symbols=_collect_symbols(tree),
        parse_error=None,
        raw_imports=_collect_raw_imports(tree, source),
    )
