"""Simple tests for parse_js.py — no pytest, just asserts."""

import sys
from pathlib import Path

# Add backend to path so we can import
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.parse_js import (
    extract_file_docstring,
    extract_imports,
    extract_symbols,
)

# ==============================================================================
# TEST 1: extract_file_docstring
# ==============================================================================

def test_docstring_at_top():
    """Should extract /** */ at the very top."""
    source = '''/** This is the file description. */
import x from "y"
'''
    result = extract_file_docstring(source)
    assert result is not None
    assert "file description" in result.lower()
    print("✓ test_docstring_at_top")


def test_no_docstring():
    """Should return None if no /** */ at top."""
    source = '''import x from "y"
function foo() {}
'''
    result = extract_file_docstring(source)
    assert result is None
    print("✓ test_no_docstring")


def test_docstring_first_sentence():
    """Should extract only first sentence (~ 60 chars)."""
    source = '''/**
 * This is the first sentence. This is the second sentence.
 * More stuff here.
 */
import x from "y"
'''
    result = extract_file_docstring(source)
    assert result is not None
    assert "first sentence" in result
    print("✓ test_docstring_first_sentence")


# ==============================================================================
# TEST 2: extract_imports
# ==============================================================================

def test_simple_import():
    """Should extract 'import x from "y"'."""
    source = 'import React from "react"\n'
    imports = extract_imports(source)
    assert len(imports) == 1
    raw, spec, line = imports[0]
    assert spec == "react"
    assert line == 1
    print("✓ test_simple_import")


def test_import_with_braces():
    """Should extract 'import {a, b} from "x"'."""
    source = 'import { useState, useEffect } from "react"\n'
    imports = extract_imports(source)
    assert len(imports) >= 1
    specs = [imp[1] for imp in imports]
    assert "react" in specs
    print("✓ test_import_with_braces")


def test_side_effect_import():
    """Should extract 'import "x"' (side-effect)."""
    source = 'import "./styles.css"\n'
    imports = extract_imports(source)
    assert len(imports) >= 1
    specs = [imp[1] for imp in imports]
    assert "./styles.css" in specs
    print("✓ test_side_effect_import")


def test_multiline_import():
    """Should detect correct START line of multi-line import."""
    source = '''import {
  useState,
  useEffect
} from "react"
'''
    imports = extract_imports(source)
    assert len(imports) >= 1
    line = imports[0][2]
    assert line == 1, f"Expected line 1, got {line}"
    print("✓ test_multiline_import")


def test_import_with_comment():
    """Should NOT extract commented-out imports."""
    source = '''// import badStuff from "bad"
import good from "good"
'''
    imports = extract_imports(source)
    specs = [imp[1] for imp in imports]
    assert "bad" not in specs
    assert "good" in specs
    print("✓ test_import_with_comment")


def test_import_in_string():
    """Should NOT extract import-like text inside strings."""
    source = 'const url = "http://example.com/import"\n'
    imports = extract_imports(source)
    assert len(imports) == 0
    print("✓ test_import_in_string")


def test_require():
    """Should extract require() calls."""
    source = 'const x = require("lodash")\n'
    imports = extract_imports(source)
    assert len(imports) >= 1
    specs = [imp[1] for imp in imports]
    assert "lodash" in specs
    print("✓ test_require")


def test_dynamic_import():
    """Should extract dynamic import()."""
    source = 'const x = await import("./module")\n'
    imports = extract_imports(source)
    assert len(imports) >= 1
    specs = [imp[1] for imp in imports]
    assert "./module" in specs
    print("✓ test_dynamic_import")


def test_export_from():
    """Should extract 'export {x} from "y"'."""
    source = 'export { Button } from "./components"\n'
    imports = extract_imports(source)
    assert len(imports) >= 1
    specs = [imp[1] for imp in imports]
    assert "./components" in specs
    print("✓ test_export_from")


# ==============================================================================
# TEST 3: extract_symbols
# ==============================================================================

def test_function_declaration():
    """Should find 'function foo() {}'."""
    source = '''function hello() {
  return "world"
}
'''
    symbols = extract_symbols(source)
    assert len(symbols) >= 1
    names = [s.name for s in symbols]
    assert "hello" in names
    print("✓ test_function_declaration")


def test_arrow_function():
    """Should find 'const foo = () => {}'."""
    source = 'const greet = () => "hi"\n'
    symbols = extract_symbols(source)
    assert len(symbols) >= 1
    names = [s.name for s in symbols]
    assert "greet" in names
    print("✓ test_arrow_function")


def test_class_declaration():
    """Should find 'class Foo {}'."""
    source = '''class MyComponent {
  render() { }
}
'''
    symbols = extract_symbols(source)
    assert len(symbols) >= 1
    names = [s.name for s in symbols]
    assert "MyComponent" in names
    print("✓ test_class_declaration")


def test_express_route():
    """Should find 'app.get("/path", ...)'."""
    source = 'app.get("/api/users", (req, res) => res.json([]))\n'
    symbols = extract_symbols(source)
    # Should have a route symbol with kind="route"
    routes = [s for s in symbols if s.kind == "route"]
    assert len(routes) >= 1
    assert any("/api/users" in s.name for s in routes)
    print("✓ test_express_route")


def test_symbol_with_jsdoc():
    """Should extract JSDoc above a symbol."""
    source = '''/**
 * Fetches user data.
 */
function getUser() { }
'''
    symbols = extract_symbols(source)
    assert len(symbols) >= 1
    user_sym = [s for s in symbols if s.name == "getUser"][0]
    assert user_sym.docstring is not None
    assert "Fetches" in user_sym.docstring
    print("✓ test_symbol_with_jsdoc")


# ==============================================================================
# RUN ALL TESTS
# ==============================================================================

if __name__ == "__main__":
    print("\n=== Running parse_js tests ===\n")
    
    # Docstring tests
    test_docstring_at_top()
    test_no_docstring()
    test_docstring_first_sentence()
    
    # Import tests
    test_simple_import()
    test_import_with_braces()
    test_side_effect_import()
    test_multiline_import()
    test_import_with_comment()
    test_import_in_string()
    test_require()
    test_dynamic_import()
    test_export_from()
    
    # Symbol tests
    test_function_declaration()
    test_arrow_function()
    test_class_declaration()
    test_express_route()
    test_symbol_with_jsdoc()
    
    print("\n✓ All tests passed!\n")
