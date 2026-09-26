"""Tests for JS/TS parser."""

from parse_js import parse_string


def test_named_imports():
    code = "import { useState, useEffect } from 'react'"
    result = parse_string(code)
    assert len(result.imports) == 1
    assert result.imports[0].spec == 'react'
    print("✅ test_named_imports passed")


def test_default_import():
    code = "import React from 'react'"
    result = parse_string(code)
    assert len(result.imports) == 1
    assert result.imports[0].spec == 'react'
    print("✅ test_default_import passed")


def test_require():
    code = "const express = require('express')"
    result = parse_string(code)
    assert any(imp.spec == 'express' for imp in result.imports)
    print("✅ test_require passed")


def test_export_from():
    code = "export { Component } from './Component'"
    result = parse_string(code)
    assert any(imp.spec == './Component' for imp in result.imports)
    assert result.imports[0].is_relative == True
    print("✅ test_export_from passed")


def test_dynamic_import():
    code = "const mod = await import('./dynamic.js')"
    result = parse_string(code)
    assert any('./dynamic.js' in imp.spec for imp in result.imports)
    print("✅ test_dynamic_import passed")


def test_express_routes():
    code = "app.get('/users/:id', handler)"
    result = parse_string(code)
    assert '/users/:id' in result.routes
    print("✅ test_express_routes passed")


def test_symbols():
    code = """
function fetchData() {}
class UserService {}
export const login = () => {}
"""
    result = parse_string(code)
    assert 'fetchData' in result.symbols
    assert 'UserService' in result.symbols
    assert 'login' in result.symbols
    print("✅ test_symbols passed")


def test_comments_stripped():
    code = """
// import { fake } from 'not-real'
/* import { alsoFake } from 'nope' */
import { actual } from 'real-import'
"""
    result = parse_string(code)
    assert len(result.imports) == 1
    assert result.imports[0].spec == 'real-import'
    print("✅ test_comments_stripped passed")


if __name__ == "__main__":
    test_named_imports()
    test_default_import()
    test_require()
    test_export_from()
    test_dynamic_import()
    test_express_routes()
    test_symbols()
    test_comments_stripped()
    print("\n✅ ALL 8 TESTS PASSED!")