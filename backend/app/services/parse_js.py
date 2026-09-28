from __future__ import annotations
import posixpath
import re
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

def _blank_comments(source: str) -> str:
    result = []
    i = 0
    while i < len(source):
        if i < len(source) - 1 and source[i:i+2] == '//':
            end = source.find('\n', i)
            if end == -1:
                result.append(' ' * (len(source) - i))
                break
            result.append(' ' * (end - i) + '\n')
            i = end + 1
        elif i < len(source) - 1 and source[i:i+2] == '/*':
            start = i
            end = source.find('*/', i + 2)
            if end == -1:
                result.append(' ' * (len(source) - i))
                break
            comment = source[i:end+2]
            blanked = ''.join('\n' if c == '\n' else ' ' for c in comment)
            result.append(blanked)
            i = end + 2
        elif source[i] in ('"', "'", '`'):
            quote = source[i]
            start = i
            i += 1
            while i < len(source):
                if source[i] == '\\':
                    i += 2
                elif source[i] == quote:
                    result.append(source[start:i+1])
                    i += 1
                    break
                else:
                    i += 1
        else:
            result.append(source[i])
            i += 1
    return ''.join(result)

def extract_file_docstring(source: str) -> Optional[str]:
    lines = source.split('\n')
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line.startswith('#!') or not line:
            idx += 1
        else:
            break
    if idx >= len(lines):
        return None
    remaining = '\n'.join(lines[idx:])
    match = re.match(r'^/\*+\s*(.*?)\s*\*+/', remaining, re.DOTALL)
    if not match:
        return None
    doc = match.group(1)
    doc_lines = []
    for line in doc.split('\n'):
        stripped = line.strip()
        if stripped.startswith('*'):
            stripped = stripped[1:].strip()
        doc_lines.append(stripped)
    doc = ' '.join(doc_lines).strip()
    first_sentence = doc.split('.')[0].strip()
    return first_sentence[:60] if first_sentence else None

def extract_imports(source: str) -> list[tuple[str, str, int]]:
    blanked = _blank_comments(source)
    imports = []
    for match in re.finditer(r'import\s+(?:(?:\{[^}]*\})|(?:\*\s+as\s+\w+)|(?:\w+)|(?:(?:default|type)\s+\w+))?\s*from\s+["\']([^"\']+)["\']', blanked, re.MULTILINE):
        raw = match.group(0)
        spec = match.group(1)
        line = blanked[:match.start()].count('\n') + 1
        imports.append((raw, spec, line))
    for match in re.finditer(r'import\s+type\s+\{[^}]*\}\s+from\s+["\']([^"\']+)["\']', blanked, re.MULTILINE):
        raw = match.group(0)
        spec = match.group(1)
        line = blanked[:match.start()].count('\n') + 1
        if (raw, spec, line) not in imports:
            imports.append((raw, spec, line))
    for match in re.finditer(r"import\s+['\"]([^'\"]+)['\"]", blanked, re.MULTILINE):
        raw = match.group(0)
        spec = match.group(1)
        line = blanked[:match.start()].count('\n') + 1
        if (raw, spec, line) not in imports:
            imports.append((raw, spec, line))
    for match in re.finditer(r'export\s+\{[^}]*\}\s+from\s+["\']([^"\']+)["\']', blanked, re.MULTILINE):
        raw = match.group(0)
        spec = match.group(1)
        line = blanked[:match.start()].count('\n') + 1
        imports.append((raw, spec, line))
    for match in re.finditer(r'export\s+\*\s+from\s+["\']([^"\']+)["\']', blanked, re.MULTILINE):
        raw = match.group(0)
        spec = match.group(1)
        line = blanked[:match.start()].count('\n') + 1
        imports.append((raw, spec, line))
    for match in re.finditer(r'require\s*\(\s*["\']([^"\']+)["\']\s*\)', blanked, re.MULTILINE):
        raw = match.group(0)
        spec = match.group(1)
        line = blanked[:match.start()].count('\n') + 1
        imports.append((raw, spec, line))
    for match in re.finditer(r'import\s*\(\s*["\']([^"\']+)["\']\s*\)', blanked, re.MULTILINE):
        raw = match.group(0)
        spec = match.group(1)
        line = blanked[:match.start()].count('\n') + 1
        imports.append((raw, spec, line))
    return imports

def _get_preceding_jsdoc(lines: list[str], symbol_line: int) -> Optional[str]:
    if symbol_line <= 1:
        return None
    line_idx = symbol_line - 2
    while line_idx >= 0:
        line = lines[line_idx].strip()
        if line.endswith('*/'):
            start_idx = line_idx
            while start_idx >= 0 and not lines[start_idx].strip().startswith('/*'):
                start_idx -= 1
            if start_idx >= 0:
                doc = '\n'.join(lines[start_idx:line_idx+1])
                doc = re.sub(r'^/\*+\s*|\s*\*+/$', '', doc)
                doc_lines = []
                for l in doc.split('\n'):
                    l = l.strip()
                    if l.startswith('*'):
                        l = l[1:].strip()
                    doc_lines.append(l)
                doc = ' '.join(doc_lines).strip()
                first_sentence = doc.split('.')[0].strip()
                return first_sentence[:60] if first_sentence else None
            return None
        elif not line or line.startswith('//'):
            line_idx -= 1
        else:
            break
    return None

def extract_symbols(source: str) -> list[SymbolRef]:
    blanked = _blank_comments(source)
    lines = source.split('\n')
    symbols = []
    for match in re.finditer(r'(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(\w+)\s*\(', blanked, re.MULTILINE):
        name = match.group(1)
        line_num = blanked[:match.start()].count('\n') + 1
        docstring = _get_preceding_jsdoc(lines, line_num)
        symbols.append(SymbolRef(name=name, kind='function', line=line_num, docstring=docstring))
    for match in re.finditer(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(?[^)]*\)\s*=>', blanked, re.MULTILINE):
        name = match.group(1)
        line_num = blanked[:match.start()].count('\n') + 1
        docstring = _get_preceding_jsdoc(lines, line_num)
        symbols.append(SymbolRef(name=name, kind='function', line=line_num, docstring=docstring))
    for match in re.finditer(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\(', blanked, re.MULTILINE):
        name = match.group(1)
        line_num = blanked[:match.start()].count('\n') + 1
        docstring = _get_preceding_jsdoc(lines, line_num)
        symbols.append(SymbolRef(name=name, kind='function', line=line_num, docstring=docstring))
    for match in re.finditer(r'(?:export\s+(?:default\s+)?)?class\s+(\w+)', blanked, re.MULTILINE):
        name = match.group(1)
        line_num = blanked[:match.start()].count('\n') + 1
        docstring = _get_preceding_jsdoc(lines, line_num)
        symbols.append(SymbolRef(name=name, kind='class', line=line_num, docstring=docstring))
    for match in re.finditer(r'(?:app|router|server)\.(get|post|put|patch|delete|options|head|all)\s*\(\s*["\']([^"\']+)["\']', blanked, re.MULTILINE):
        method = match.group(1).upper()
        path = match.group(2)
        line_num = blanked[:match.start()].count('\n') + 1
        name = f'{method} {path}'
        docstring = _get_preceding_jsdoc(lines, line_num)
        symbols.append(SymbolRef(name=name, kind='route', line=line_num, route_path=path, route_methods=[method], docstring=docstring))
    return symbols

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