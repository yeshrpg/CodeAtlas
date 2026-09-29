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
    """Extract first /** */ block at top of file, return first sentence."""
    lines = source.split('\n')
    i = 0
    # Skip empty lines and shebang
    while i < len(lines) and (not lines[i].strip() or lines[i].startswith('#')):
        i += 1
    
    if i >= len(lines):
        return None
    
    line = lines[i].strip()
    if not line.startswith(('/**', '/*')):
        return None
    
    # Single-line comment
    if '**/' in line or '*/' in line:
        text = line.replace('/**', '').replace('/*', '').replace('*/', '').strip()
        return text[:60] if text else None
    
    # Multi-line comment
    comment_lines = [line.replace('/**', '').replace('/*', '').strip()]
    i += 1
    
    while i < len(lines):
        line = lines[i]
        if '*/' in line:
            text = line.split('*/')[0].strip()
            if text.startswith('*'):
                text = text[1:].strip()
            comment_lines.append(text)
            break
        text = line.strip()
        if text.startswith('*'):
            text = text[1:].strip()
        if text:
            comment_lines.append(text)
        i += 1
    
    full_text = ' '.join(comment_lines)
    match = re.match(r'^([^.!?]*[.!?])', full_text)
    first_sentence = match.group(1).strip() if match else full_text
    return first_sentence[:60] if first_sentence else None
def extract_imports(source: str) -> list[tuple[str, str, int]]:
    """Extract all import/require statements: (raw, specifier, line)."""
    
    # Blank out comments while preserving newlines
    def blank_comments(src: str) -> str:
        result = []
        i = 0
        while i < len(src):
            # Handle strings (single, double, backtick)
            if src[i] in ('"', "'", "`"):
                quote = src[i]
                result.append(src[i])
                i += 1
                while i < len(src):
                    if src[i] == '\\' and i + 1 < len(src):
                        result.append(src[i:i+2])
                        i += 2
                    elif src[i] == quote:
                        result.append(src[i])
                        i += 1
                        break
                    else:
                        result.append(src[i])
                        i += 1
            # Handle // comments
            elif i < len(src) - 1 and src[i:i+2] == '//':
                while i < len(src) and src[i] != '\n':
                    result.append(' ')
                    i += 1
                if i < len(src):
                    result.append(src[i])
                    i += 1
            # Handle /* */ comments
            elif i < len(src) - 1 and src[i:i+2] == '/*':
                result.append(' ')
                result.append(' ')
                i += 2
                while i < len(src) - 1:
                    if src[i:i+2] == '*/':
                        result.append(' ')
                        result.append(' ')
                        i += 2
                        break
                    elif src[i] == '\n':
                        result.append('\n')
                    else:
                        result.append(' ')
                    i += 1
            else:
                result.append(src[i])
                i += 1
        return ''.join(result)
    
    cleaned = blank_comments(source)
    lines = cleaned.split('\n')
    
    imports = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        line_num = i + 1
        
        # Pattern: import ... from 'x'
        if re.search(r'\bimport\b', line):
            match = re.search(r'from\s+["\']([^"\']+)["\']', line)
            if match:
                imports.append((line.strip(), match.group(1), line_num))
                i += 1
                continue
            
            # Multiline import: { ... } from 'x'
            if '{' in line and 'from' not in line:
                raw_lines = [line]
                j = i + 1
                while j < len(lines):
                    raw_lines.append(lines[j])
                    if 'from' in lines[j]:
                        m = re.search(r'from\s+["\']([^"\']+)["\']', lines[j])
                        if m:
                            raw = '\n'.join(raw_lines).strip()
                            imports.append((raw, m.group(1), line_num))
                            i = j + 1
                            break
                    j += 1
                else:
                    i = j
                continue
            
            # import 'x' (side-effect)
            match = re.search(r'import\s+["\']([^"\']+)["\']', line)
            if match:
                imports.append((line.strip(), match.group(1), line_num))
                i += 1
                continue
        
        # Pattern: import type {x} from 'y'
        if 'import type' in line:
            match = re.search(r'from\s+["\']([^"\']+)["\']', line)
            if match:
                imports.append((line.strip(), match.group(1), line_num))
                i += 1
                continue
        
        # Pattern: export {x} from 'y' or export * from 'y'
        if 'export' in line and 'from' in line:
            match = re.search(r'from\s+["\']([^"\']+)["\']', line)
            if match:
                imports.append((line.strip(), match.group(1), line_num))
                i += 1
                continue
        
        # Pattern: require('x')
        match = re.search(r'require\s*\(\s*["\']([^"\']+)["\']\s*\)', line)
        if match:
            imports.append((line.strip(), match.group(1), line_num))
            i += 1
            continue
        
        # Pattern: import('x') dynamic
        match = re.search(r'import\s*\(\s*["\']([^"\']+)["\']\s*\)', line)
        if match:
            imports.append((line.strip(), match.group(1), line_num))
            i += 1
            continue
        
        i += 1
    
    return imports

def extract_symbols(source: str) -> list[SymbolRef]:
    """Extract top-level functions, classes, and Express routes."""
    
    # Blank comments
    def blank_comments(src: str) -> str:
        result = []
        i = 0
        while i < len(src):
            if src[i] in ('"', "'", "`"):
                quote = src[i]
                result.append(src[i])
                i += 1
                while i < len(src):
                    if src[i] == '\\' and i + 1 < len(src):
                        result.append(src[i:i+2])
                        i += 2
                    elif src[i] == quote:
                        result.append(src[i])
                        i += 1
                        break
                    else:
                        result.append(src[i])
                        i += 1
            elif i < len(src) - 1 and src[i:i+2] == '//':
                while i < len(src) and src[i] != '\n':
                    result.append(' ')
                    i += 1
                if i < len(src):
                    result.append(src[i])
                    i += 1
            elif i < len(src) - 1 and src[i:i+2] == '/*':
                result.append(' ')
                result.append(' ')
                i += 2
                while i < len(src) - 1:
                    if src[i:i+2] == '*/':
                        result.append(' ')
                        result.append(' ')
                        i += 2
                        break
                    elif src[i] == '\n':
                        result.append('\n')
                    else:
                        result.append(' ')
                    i += 1
            else:
                result.append(src[i])
                i += 1
        return ''.join(result)
    
    def extract_jsdoc(lines: list[str], sym_line: int) -> Optional[str]:
        """Extract JSDoc block directly above symbol."""
        if sym_line <= 1:
            return None
        
        idx = sym_line - 2  # Line before symbol (0-indexed)
        if idx < 0 or '*/' not in lines[idx]:
            return None
        
        # Find opening /**
        start_idx = idx
        while start_idx >= 0:
            if '/**' in lines[start_idx]:
                comment_text = []
                for i in range(start_idx, idx + 1):
                    text = lines[i]
                    text = text.replace('/**', '').replace('*/', '').strip()
                    if text.startswith('*'):
                        text = text[1:].strip()
                    if text:
                        comment_text.append(text)
                
                full = ' '.join(comment_text)
                match = re.match(r'^([^.!?]*[.!?])', full)
                result = match.group(1).strip() if match else full
                return result[:60] if result else None
            start_idx -= 1
        
        return None
    
    cleaned = blank_comments(source)
    lines = cleaned.split('\n')
    raw_lines = source.split('\n')
    symbols = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        line_num = i + 1
        stripped = line.strip()
        
        if not stripped:
            i += 1
            continue
        
        docstring = extract_jsdoc(raw_lines, line_num)
        
        # Pattern 1: function f() or async function f() or export function f()
        match = re.match(r'^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)', stripped)
        if match:
            symbols.append(SymbolRef(
                name=match.group(1),
                kind="function",
                line=line_num,
                docstring=docstring,
            ))
            i += 1
            continue
        
        # Pattern 2: class C() or export class C()
        match = re.match(r'^(?:export\s+)?(?:default\s+)?class\s+(\w+)', stripped)
        if match:
            symbols.append(SymbolRef(
                name=match.group(1),
                kind="class",
                line=line_num,
                docstring=docstring,
            ))
            i += 1
            continue
        
        # Pattern 3: const f = () => or const f = async () =>
        match = re.match(r'^(?:export\s+)?(?:default\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(', stripped)
        if match:
            symbols.append(SymbolRef(
                name=match.group(1),
                kind="function",
                line=line_num,
                docstring=docstring,
            ))
            i += 1
            continue
        
        # Pattern 4: const f = function() or const f = async function()
        match = re.match(r'^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function', stripped)
        if match:
            symbols.append(SymbolRef(
                name=match.group(1),
                kind="function",
                line=line_num,
                docstring=docstring,
            ))
            i += 1
            continue
        
        # Pattern 5: Express routes - app.get|post|put|patch|delete|options|head|all('/path', ...)
        match = re.match(r'^(?:app|router|server)\.(get|post|put|patch|delete|options|head|all)\s*\(\s*["\']([^"\']+)["\']', stripped)
        if match:
            method = match.group(1).upper()
            path = match.group(2)
            name = f"{method} {path}"
            symbols.append(SymbolRef(
                name=name,
                kind="route",
                line=line_num,
                docstring=docstring,
                route_path=path,
                route_methods=[method],
            ))
            i += 1
            continue
        
        i += 1
    
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