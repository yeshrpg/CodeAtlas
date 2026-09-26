"""Tests for fallback heuristic labels."""

from fallback import heuristic_labels, determine_layer, get_summary


def test_label_from_folder():
    """Test: label from folder name"""
    components = [
        {
            'id': 'src/auth',
            'files': [],
            'symbols': []
        }
    ]
    result = heuristic_labels(components)
    assert result['components'][0]['label'] == 'Auth'
    print("✅ test_label_from_folder passed")


def test_layer_from_keyword():
    """Test: layer from keywords"""
    assert determine_layer('src/routes') == 'api'
    assert determine_layer('src/services') == 'service'
    assert determine_layer('src/models') == 'data'
    assert determine_layer('src/utils') == 'util'
    assert determine_layer('src/components') == 'ui'
    assert determine_layer('src/config') == 'config'
    assert determine_layer('src/other') == 'other'
    print("✅ test_layer_from_keyword passed")


def test_summary_from_docstring():
    """Test: summary from first docstring"""
    components = [
        {
            'id': 'src/auth',
            'files': [
                {
                    'path': 'src/auth/routes.py',
                    'doc_first_line': 'Handle user authentication and tokens'
                }
            ],
            'symbols': []
        }
    ]
    result = heuristic_labels(components)
    summary = result['components'][0]['summary']
    assert 'Handle user authentication' in summary
    print("✅ test_summary_from_docstring passed")


def test_summary_from_file_count():
    """Test: summary from file count if no docstring"""
    components = [
        {
            'id': 'src/utils',
            'files': [
                {'path': 'src/utils/a.py', 'doc_first_line': ''},
                {'path': 'src/utils/b.py', 'doc_first_line': ''},
                {'path': 'src/utils/c.py', 'doc_first_line': ''}
            ],
            'symbols': []
        }
    ]
    result = heuristic_labels(components)
    summary = result['components'][0]['summary']
    assert '3 files' in summary
    print("✅ test_summary_from_file_count passed")


def test_reading_order():
    """Test: reading order (entry files first)"""
    components = [
        {
            'id': 'src',
            'files': [
                {
                    'path': 'src/main.py',
                    'doc_first_line': 'Entry point',
                    'imported_by': []
                },
                {
                    'path': 'src/utils.py',
                    'doc_first_line': '',
                    'imported_by': ['src/main.py', 'src/other.py']
                }
            ],
            'symbols': []
        }
    ]
    result = heuristic_labels(components)
    order = result['reading_order']
    
    # Entry point should be first
    assert order[0]['path'] == 'src/main.py'
    assert order[0]['reason'] == 'entry point'
    print("✅ test_reading_order passed")


if __name__ == "__main__":
    test_label_from_folder()
    test_layer_from_keyword()
    test_summary_from_docstring()
    test_summary_from_file_count()
    test_reading_order()
    print("\n✅ ALL 5 TESTS PASSED!")