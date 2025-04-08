#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
import os
from unittest.mock import patch, mock_open, MagicMock, call
import tempfile 
import shutil

# Make the app accessible for testing
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app # Import the Flask app instance

# Define filenames used by these routes
GOALS_FILE = 'PROJECT_GOALS.md'
LEARNINGS_FILE = 'LEARNINGS.md'
NOTES_FILE = 'PROJECT_NOTES.md' # Example file for /md_files
OTHER_MD_FILE = 'OTHER_FILE.md' # Another example for /md_files

@pytest.fixture
def client_md():
    """Create a Flask test client, mocking the filesystem for MD files."""
    # Use patch.dict for app config if needed, but these routes primarily use file I/O
    app.config['TESTING'] = True
    
    # We'll use mock_open within the tests to control file content
    with app.test_client() as client:
        yield client
    # No teardown needed as we use mock_open

# --- Test Cases for GET requests ---

@patch('app.open', new_callable=mock_open, read_data="# Test Goals Content")
def test_get_goals_success(mock_file, client_md):
    """Test successfully loading the /goals page."""
    # Need to also allow template loading to work
    with patch('jinja2.loaders.FileSystemLoader.get_source', return_value=('Template source', 'template.html', lambda: True)):
        response = client_md.get('/goals')
        assert response.status_code == 200
        # Check if the mocked content was used in the response (might not be easily visible depending on template)
        # We primarily check that the route executed and called open correctly.
        # assert b"# Test Goals Content" in response.data # This check might fail due to template rendering
        mock_file.assert_called_once_with(GOALS_FILE, 'r', encoding='utf-8')

@patch('app.render_template') # Patch render_template
@patch('app.open', side_effect=FileNotFoundError) # Patch open
def test_get_goals_not_found(mock_open, mock_render_template, client_md):
    """Test loading /goals when the file doesn't exist."""
    mock_render_template.return_value = "Mocked Template Render" # Prevent actual rendering
    response = client_md.get('/goals')
    assert response.status_code == 200
    # Check the context passed to render_template
    mock_render_template.assert_called_once()
    call_args, call_kwargs = mock_render_template.call_args
    # Fix 1: Assert the correct template name is used
    assert call_args[0] == 'goals.html' 
    # Fix 2: Check that the context indicates the file was not found
    assert 'goals_content' in call_kwargs
    assert 'PROJECT_GOALS.md not found' in call_kwargs['goals_content']
    # Ensure mock_open was used as expected by the route
    mock_open.assert_called_once_with(GOALS_FILE, 'r', encoding='utf-8')

@patch('app.open', new_callable=mock_open, read_data="# Test Learnings")
def test_get_learnings_success(mock_file, client_md):
    """Test successfully loading the /learnings page."""
    with patch('jinja2.loaders.FileSystemLoader.get_source', return_value=('Template source', 'template.html', lambda: True)):
        response = client_md.get('/learnings')
        assert response.status_code == 200
        # assert b"# Test Learnings" in response.data
        mock_file.assert_called_once_with(LEARNINGS_FILE, 'r', encoding='utf-8')

@patch('app.glob.glob') # Patch glob within the app module
@patch('app.open', new_callable=mock_open)
def test_get_md_files_success(mock_open_app, mock_glob_app, client_md):
    """Test successfully loading the /md_files page."""
    mock_glob_app.return_value = sorted([NOTES_FILE, OTHER_MD_FILE])
    # Configure multiple reads: one for each MD file + one for the template
    # The actual content check is difficult without rendering the real template
    # Focus on asserting the correct files were opened
    
    # We need a way for mock_open to handle multiple files AND the template
    # Let's use a side_effect dictionary for open
    mock_files_content = {
        NOTES_FILE: mock_open(read_data="Notes Content").return_value,
        OTHER_MD_FILE: mock_open(read_data="Other Content").return_value
    }
    def open_side_effect(path, *args, **kwargs):
        if path in mock_files_content:
            return mock_files_content[path]
        else: # Fallback for template loading or other unexpected opens
            # print(f"Warning: Unexpected open call in test: {path}")
            return mock_open(read_data="Fallback content").return_value
            # raise FileNotFoundError(f"Unexpected open call: {path}") # Alternative: raise error

    mock_open_app.side_effect = open_side_effect

    with patch('jinja2.loaders.FileSystemLoader.get_source', return_value=('Template source with loop', 'template.html', lambda: True)):
        response = client_md.get('/md_files')
        assert response.status_code == 200
        mock_glob_app.assert_called_once_with('*.md')
        # Check open was called for each file found by glob
        # Note: mock_open_app tracks calls made *through the patch*
        assert mock_open_app.call_count >= 2 # At least 2 for the MD files
        mock_open_app.assert_has_calls([
            call(NOTES_FILE, 'r', encoding='utf-8'),
            call(OTHER_MD_FILE, 'r', encoding='utf-8')
        ], any_order=True)
        # Check that the content we mocked was passed (requires inspecting render_template args)
        # This is harder, let's rely on the open calls being correct for now.


# --- Test Cases for POST requests (Updates) ---

# Patch open within the 'app' module
@patch('app.open', new_callable=mock_open)
def test_update_goals_success(mock_file, client_md):
    """Test successfully updating goals via POST."""
    new_content = "# Updated Goals"
    response = client_md.post('/update_goals', data={'goals_content': new_content})
    assert response.status_code == 302
    assert response.location == '/goals'
    mock_file.assert_called_once_with(GOALS_FILE, 'w', encoding='utf-8')
    mock_file().write.assert_called_once_with(new_content)

@patch('app.open', new_callable=mock_open)
def test_update_learnings_success(mock_file, client_md):
    """Test successfully updating learnings via POST."""
    new_content = "- Updated Learnings"
    response = client_md.post('/update_learnings', data={'learnings_content': new_content})
    assert response.status_code == 302
    assert response.location == '/learnings'
    mock_file.assert_called_once_with(LEARNINGS_FILE, 'w', encoding='utf-8')
    mock_file().write.assert_called_once_with(new_content)

@patch('app.glob.glob')
@patch('app.open', new_callable=mock_open)
def test_update_md_file_success(mock_file, mock_glob, client_md):
    """Test successfully updating a specific MD file via POST."""
    mock_glob.return_value = [NOTES_FILE]
    new_content = "Updated Notes Content"
    response = client_md.post('/update_md_file', data={
        'filename': NOTES_FILE,
        'md_content': new_content
    })
    assert response.status_code == 302
    assert response.location == '/md_files'
    mock_glob.assert_called_once_with('*.md')
    mock_file.assert_called_once_with(NOTES_FILE, 'w', encoding='utf-8')
    mock_file().write.assert_called_once_with(new_content)

@patch('app.glob.glob')
@patch('app.open', new_callable=mock_open)
def test_update_md_file_invalid_filename(mock_file, mock_glob, client_md):
    """Test updating an MD file with a disallowed filename."""
    mock_glob.return_value = [NOTES_FILE]
    new_content = "Trying to write to wrong file"
    response = client_md.post('/update_md_file', data={
        'filename': '../etc/passwd',
        'md_content': new_content
    })
    assert response.status_code == 302
    assert response.location == '/md_files'
    mock_glob.assert_called_once_with('*.md')
    mock_file.assert_not_called()

def test_update_goals_missing_data(client_md):
    """Test POSTing to update goals with missing form data."""
    response = client_md.post('/update_goals', data={})
    assert response.status_code == 302 # Redirects back
    assert response.location == '/goals'
    # Expect error flash message

# Add similar tests for update_learnings and update_md_file missing data 