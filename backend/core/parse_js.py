"""
JavaScript/TypeScript parser for CodeAtlas.
Detects: imports, exports, requires, dynamic imports, routes, symbols, docstrings.
"""

import re
from typing import List


class ImportRef:
    """One import statement"""
    def __init__(self, spec: str, line: int, stmt: str, is_relative: bool = False, is_package: bool = False, names: List[str] = None):
        self.spec = spec
        self.line = line
        self.stmt = stmt
        self.is_relative = is_relative
        self.is_package = is_package
        self.names = names or []
        self.resolved_path = None


class ParsedFile:
    """Result of parsing one file"""
    def __init__(self, path: str, lang: str = "javascript"):
        self.path = path
        self.lang = lang
        self.symbols = []
        self.imports = []
        self.unresolved = []
        self.doc_first_line = ""
        self.libs = []
        self.routes = []


def strip_comments(content: str) -> str:
    """Strip // and /* */ comments from JS/TS code."""
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    return content


def detect_imports(content: str) -> List[ImportRef]:
    """Detect all import/require/export statements."""
    imports = []
    
    patterns = [
        (r"import\s+(?:\{[^}]*\}|[\w*]+)\s+from\s+['\"]([^'\"]+)['\"]", ["import-named"]),
        (r"import\s+['\"]([^'\"]+)['\"]", ["import-side"]),
        (r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", ["require"]),
        (r"export\s+(?:\{[^}]*\}|[\w*]+)\s+from\s+['\"]([^'\"]+)['\"]", ["export"]),
        (r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", ["dynamic-import"]),
    ]
    
    for pattern, names in patterns:
        for match in re.finditer(pattern, content):
            spec = match.group(1)
            line = content[:match.start()].count('\n') + 1
            stmt = match.group(0)
            
            imp = ImportRef(
                spec=spec,
                line=line,
                stmt=stmt,
                is_relative=spec.startswith('.'),
                is_package=not spec.startswith('.'),
                names=names
            )
            
            if not any(i.spec == spec and i.line == line for i in imports):
                imports.append(imp)
    
    return imports


def detect_symbols(content: str) -> List[str]:
    """Detect top-level function, class, and const names."""
    symbols = []
    
    for match in re.finditer(r"^function\s+(\w+)\s*\(", content, re.MULTILINE):
        symbols.append(match.group(1))
    
    for match in re.finditer(r"^class\s+(\w+)", content, re.MULTILINE):
        symbols.append(match.group(1))
    
    for match in re.finditer(r"export\s+const\s+(\w+)", content, re.MULTILINE):
        symbols.append(match.group(1))
    
    return list(set(symbols))


def detect_routes(content: str) -> List[str]:
    """Detect Express-style routes."""
    routes = []
    pattern = r"(?:app|router)\.(get|post|put|delete|patch|use)\s*\(\s*['\"]([^'\"]+)['\"]"
    
    for match in re.finditer(pattern, content):
        route = match.group(2)
        if route not in routes:
            routes.append(route)
    
    return routes


def extract_first_comment(content: str) -> str:
    """Extract the first comment or docstring line."""
    match = re.search(r'/\*\*\s*\n\s*\*\s*([^*]+)', content)
    if match:
        return match.group(1).strip()[:120]
    
    match = re.search(r'^\s*//\s*(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()[:120]
    
    return ""


def parse(file_path: str) -> ParsedFile:
    """Parse a JS/TS file and return ParsedFile object."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ParsedFile(file_path, "javascript")
    
    clean_content = strip_comments(content)
    
    result = ParsedFile(file_path, "javascript")
    result.imports = detect_imports(clean_content)
    result.symbols = detect_symbols(clean_content)
    result.routes = detect_routes(clean_content)
    result.doc_first_line = extract_first_comment(content)
    result.libs = list(set([imp.spec for imp in result.imports if imp.is_package]))
    result.unresolved = [imp.spec for imp in result.imports if imp.is_package and imp.resolved_path is None]
    
    return result


def parse_string(code: str) -> ParsedFile:
    """Parse JS/TS code from a string (for testing)."""
    clean_content = strip_comments(code)
    
    result = ParsedFile("test.js", "javascript")
    result.imports = detect_imports(clean_content)
    result.symbols = detect_symbols(clean_content)
    result.routes = detect_routes(clean_content)
    result.doc_first_line = extract_first_comment(code)
    result.libs = list(set([imp.spec for imp in result.imports if imp.is_package]))
    result.unresolved = [imp.spec for imp in result.imports if imp.is_package and imp.resolved_path is None]
    
    return result