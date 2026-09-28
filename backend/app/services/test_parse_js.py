import pytest
from app.services.parse_js import extract_imports, extract_symbols, extract_file_docstring

def test_extract_file_docstring():
    src = "const x = 1;"
    result = extract_file_docstring(src)
    assert result is None

def test_extract_imports():
    src = "import React from 'react';"
    imports = extract_imports(src)
    assert len(imports) > 0

def test_extract_symbols():
    src = "function test() { }"
    symbols = extract_symbols(src)
    assert len(symbols) > 0