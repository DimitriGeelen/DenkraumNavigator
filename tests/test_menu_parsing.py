import pytest
import os
from unittest.mock import mock_open, patch

# Adjust the import path based on your project structure
# Assuming app.py is in the root and tests are in tests/
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import parse_menu_file, app as flask_app # Import the function and the app instance

# Sample content for a valid menu.md file
VALID_MENU_CONTENT = """
# Main Navigation Menu Items

# Format: - Text: flask_endpoint_name

- Search: index
- Browse: browse
- History & Backups: history
# - Goals: display_project_goals # Old entry - Make sure this line is actually removed or commented in the test data
- Learnings: display_learnings
- MD Files: display_md_files
"""

# Menu content with comments and blank lines
MIXED_MENU_CONTENT = """
# Some comment

- First Item: first

  # Indented comment
- Second Item : second # Trailing comment
-Third No Space: third
"""

# Menu content with invalid lines
INVALID_MENU_CONTENT = """
- Valid: valid
Invalid Line
- Missing Colon
- Good : good
-: MissingText
- Spaced Colon : spaced
"""

# Expected result for VALID_MENU_CONTENT
EXPECTED_VALID_MENU = [
    {'text': 'Search', 'endpoint': 'index'},
    {'text': 'Browse', 'endpoint': 'browse'},
    {'text': 'History & Backups', 'endpoint': 'history'},
    {'text': 'Learnings', 'endpoint': 'display_learnings'},
    {'text': 'MD Files', 'endpoint': 'display_md_files'}
]

# Expected result for MIXED_MENU_CONTENT
EXPECTED_MIXED_MENU = [
    {'text': 'First Item', 'endpoint': 'first'},
    {'text': 'Second Item', 'endpoint': 'second'},
    {'text': 'Third No Space', 'endpoint': 'third'}
]

# Expected result for INVALID_MENU_CONTENT
EXPECTED_INVALID_MENU = [
    {'text': 'Valid', 'endpoint': 'valid'},
    {'text': 'Good', 'endpoint': 'good'},
    {'text': 'Spaced Colon', 'endpoint': 'spaced'}
]

@pytest.fixture
def mock_logger(mocker):
    """Mocks the logger used in the app."""
    return mocker.patch('app.logger') # Patch logger in the app module

def test_parse_valid_menu(mock_logger):
    """Test parsing a correctly formatted menu file."""
    with patch('builtins.open', mock_open(read_data=VALID_MENU_CONTENT)) as mock_file:
        result = parse_menu_file('dummy_menu.md')
        assert result == EXPECTED_VALID_MENU
        mock_file.assert_called_once_with('dummy_menu.md', 'r', encoding='utf-8')

def test_parse_mixed_content(mock_logger):
    """Test parsing a menu file with comments and blank lines."""
    with patch('builtins.open', mock_open(read_data=MIXED_MENU_CONTENT)) as mock_file:
        result = parse_menu_file('mixed_menu.md')
        assert result == EXPECTED_MIXED_MENU

def test_parse_invalid_lines(mock_logger):
    """Test parsing a menu file with some invalid lines (should skip them)."""
    with patch('builtins.open', mock_open(read_data=INVALID_MENU_CONTENT)) as mock_file:
        result = parse_menu_file('invalid_menu.md')
        assert result == EXPECTED_INVALID_MENU
        # Check if warnings were logged (optional)
        assert mock_logger.warning.call_count >= 2 # 'Invalid Line' and '- Missing Colon' and '-: MissingText' should maybe log warnings

def test_parse_file_not_found(mock_logger):
    """Test parsing when the menu file does not exist."""
    with patch('builtins.open', side_effect=FileNotFoundError):
        result = parse_menu_file('nonexistent_menu.md')
        assert result == []
        mock_logger.error.assert_called_with("Menu file not found: nonexistent_menu.md. Returning empty menu.")

def test_app_main_menu_loaded():
    """Test if the main_menu loaded by the app instance matches the file content."""
    # This test relies on the actual menu.md file existing and being parseable
    # It reads the global main_menu variable loaded by the app
    from app import main_menu # Import the already loaded variable
    # Assuming the current menu.md is the same as VALID_MENU_CONTENT used above
    # You might want to read the actual menu.md here for a more robust test
    assert main_menu == EXPECTED_VALID_MENU
    assert len(main_menu) == 5 # Check the current count 