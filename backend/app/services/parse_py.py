"""
parse_py.py — AST-based parser for a single Python source file.

Locked spec constraints honored here:
- Python parsed with stdlib `ast` only (no third-party parser).
- Must NEVER crash the overall scan on a bad file: syntax errors / decode
  errors are caught and the file is marked unparseable, with a reason,
  instead of raising.
- POSIX paths everywhere (`.as_posix()`), including in every ImportRef /
  ParsedFile path field.
- Route decorators are detected heuristically (Flask/FastAPI/Django-ish)
  since this is used for API-surface hints, not guaranteed-correct
  framework introspection.

Public API:
    parse_python_file(abs_path: Path, repo_root: Path) -> ParsedFile

ParsedFile fields populated here (matches schema.py's Pydantic v2 model):
    path: str                  (POSIX, relative to repo_root)
    language: str = "python"
    line_count: int
    docstring: str | None
    imports: list[ImportRef]
    symbols: list[SymbolRef]
    routes: list[str]          (raw route path strings found, best-effort)
    parse_error: str | None    (set + all other fields empty/defaulted if
                                 the file could not be parsed)
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

try:
    # Real schema import when running inside the actual backend package.
    from ..schema import ImportRef, ParsedFile, SymbolRef
except ImportError:  # pragma: no cover - fallback for standalone/local testing only
    from dataclasses import dataclass, field

    @dataclass
    class ImportRef:
        module: str
        names: list
        is_relative: bool
        level: int
        line: int

    @dataclass
    class SymbolRef:
        name: str
        kind: str
        line: int
        end_line: Optional[int] = None

    @dataclass
    class ParsedFile:
        path: str
        language: str = "python"
        line_count: int = 0
        docstring: Optional[str] = None
        imports: list = field(default_factory=list)
        symbols: list = field(default_factory=list)
        routes: list = field(default_factory=list)
        parse_error: Optional[str] = None


# Decorator name fragments that indicate an HTTP route registration.
# Matched against the *last* attribute segment of the decorator call,
# e.g. @app.get(...) -> "get", @router.post(...) -> "post".
_ROUTE_DECORATOR_METHODS = {
    "get", "post", "put", "patch", "delete", "options", "head",
    "route",  # Flask's generic @app.route("/x", methods=[...])
}


def _to_posix_rel(abs_path: Path, repo_root: Path) -> str:
    try:
        rel = abs_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        # Not under repo_root for some reason — fall back to the raw name
        # rather than raising; this is a best-effort path label only.
        rel = Path(abs_path.name)
    return rel.as_posix()


def _decorator_route_string(dec: ast.expr) -> Optional[str]:
    """
    Return the literal route path string from a decorator call if it looks
    like an HTTP route registration, else None. Handles:
        @app.get("/foo")
        @router.post("/bar/{id}")
        @app.route("/baz", methods=["GET"])
    Does NOT attempt to resolve variables or f-strings — those are skipped
    (best-effort only, per spec: heuristic, not guaranteed).
    """
    if not isinstance(dec, ast.Call):
        return None
    func = dec.func
    method_name = None
    if isinstance(func, ast.Attribute):
        method_name = func.attr
    elif isinstance(func, ast.Name):
        method_name = func.id
    if method_name not in _ROUTE_DECORATOR_METHODS:
        return None
    if not dec.args:
        return None
    first_arg = dec.args[0]
    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
        return first_arg.value
    return None


def _collect_imports(tree: ast.Module) -> list:
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    ImportRef(
                        module=alias.name,
                        names=[],
                        is_relative=False,
                        level=0,
                        line=node.lineno,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(
                ImportRef(
                    module=module,
                    names=[alias.name for alias in node.names],
                    is_relative=node.level > 0,
                    level=node.level,
                    line=node.lineno,
                )
            )
    return imports


def _collect_symbols(tree: ast.Module) -> tuple:
    """Returns (symbols, routes). Only top-level and class-level defs are
    recorded as symbols (per spec: top-level symbols); routes are collected
    from decorators found anywhere at module/class scope."""
    symbols = []
    routes = []

    def visit_body(body, kind_for_def="function"):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(
                    SymbolRef(
                        name=node.name,
                        kind="async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                        line=node.lineno,
                        end_line=getattr(node, "end_lineno", None),
                    )
                )
                for dec in node.decorator_list:
                    route = _decorator_route_string(dec)
                    if route:
                        routes.append(route)
            elif isinstance(node, ast.ClassDef):
                symbols.append(
                    SymbolRef(
                        name=node.name,
                        kind="class",
                        line=node.lineno,
                        end_line=getattr(node, "end_lineno", None),
                    )
                )
                # Recurse one level into class body for methods (still
                # "top-level-ish": methods are meaningful symbols for a
                # component's public surface).
                visit_body(node.body, kind_for_def="method")

    visit_body(tree.body)
    return symbols, routes


def parse_python_file(abs_path: Path, repo_root: Path) -> "ParsedFile":
    """
    Parse one Python file. Never raises: on any failure (unreadable,
    undecodable, syntax error) returns a ParsedFile with parse_error set
    and every other field at its default/empty value, so the caller
    (scan/orchestration) can keep going and just note the file as
    unparseable rather than aborting the whole repo analysis.
    """
    rel_path = _to_posix_rel(abs_path, repo_root)

    try:
        source = abs_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return ParsedFile(
            path=rel_path,
            language="python",
            line_count=0,
            docstring=None,
            imports=[],
            symbols=[],
            routes=[],
            parse_error=f"read_error: {exc}",
        )

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError as exc:
        return ParsedFile(
            path=rel_path,
            language="python",
            line_count=len(source.splitlines()),
            docstring=None,
            imports=[],
            symbols=[],
            routes=[],
            parse_error=f"syntax_error: line {exc.lineno}: {exc.msg}",
        )

    docstring = ast.get_docstring(tree)
    imports = _collect_imports(tree)
    symbols, routes = _collect_symbols(tree)
    line_count = len(source.splitlines())

    return ParsedFile(
        path=rel_path,
        language="python",
        line_count=line_count,
        docstring=docstring,
        imports=imports,
        symbols=symbols,
        routes=routes,
        parse_error=None,
    )
