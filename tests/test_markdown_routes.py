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

@patch('builtins.open', new_callable=mock_open, read_data="# Test Goals Content")
def test_get_goals_success(mock_file, client_md):
    """Test successfully loading the /goals page."""
    response = client_md.get('/goals')
    assert response.status_code == 200
    assert b"# Test Goals Content" in response.data
    mock_file.assert_called_once_with(GOALS_FILE, 'r', encoding='utf-8')

@patch('builtins.open', side_effect=FileNotFoundError)
def test_get_goals_not_found(mock_file, client_md):
    """Test loading /goals when the file doesn't exist."""
    response = client_md.get('/goals')
    assert response.status_code == 200 # Route handles FileNotFoundError gracefully
    assert bytes(f"# {GOALS_FILE} not found", 'utf-8') in response.data

@patch('builtins.open', new_callable=mock_open, read_data="# Test Learnings")
def test_get_learnings_success(mock_file, client_md):
    """Test successfully loading the /learnings page."""
    response = client_md.get('/learnings')
    assert response.status_code == 200
    assert b"# Test Learnings" in response.data
    mock_file.assert_called_once_with(LEARNINGS_FILE, 'r', encoding='utf-8')

@patch('glob.glob') # Mock glob used by /md_files
@patch('builtins.open', new_callable=mock_open, read_data="Default Content")
def test_get_md_files_success(mock_file, mock_glob, client_md):
    """Test successfully loading the /md_files page."""
    # Simulate finding specific MD files
    mock_glob.return_value = sorted([NOTES_FILE, OTHER_MD_FILE])
    # Set up mock_open to return different content for different files
    mock_file().read.side_effect = ["Notes Content", "Other Content"]
    
    response = client_md.get('/md_files')
    assert response.status_code == 200
    assert bytes(NOTES_FILE, 'utf-8') in response.data
    assert bytes(OTHER_MD_FILE, 'utf-8') in response.data
    assert b"Notes Content" in response.data
    assert b"Other Content" in response.data
    mock_glob.assert_called_once_with('*.md')
    # Check open was called for each file found by glob
    assert mock_file.call_count == 2
    mock_file.assert_has_calls([
        call(NOTES_FILE, 'r', encoding='utf-8'),
        call(OTHER_MD_FILE, 'r', encoding='utf-8')
    ], any_order=True) # Order depends on sorted glob result

# --- Test Cases for POST requests (Updates) ---

@patch('builtins.open', new_callable=mock_open)
def test_update_goals_success(mock_file, client_md):
    """Test successfully updating goals via POST."""
    new_content = "# Updated Goals"
    response = client_md.post('/update_goals', data={'goals_content': new_content})
    # Check redirect
    assert response.status_code == 302
    assert response.location == '/goals'
    # Check file write
    mock_file.assert_called_once_with(GOALS_FILE, 'w', encoding='utf-8')
    mock_file().write.assert_called_once_with(new_content)

@patch('builtins.open', new_callable=mock_open)
def test_update_learnings_success(mock_file, client_md):
    """Test successfully updating learnings via POST."""
    new_content = "- Updated Learnings"
    response = client_md.post('/update_learnings', data={'learnings_content': new_content})
    assert response.status_code == 302
    assert response.location == '/learnings'
    mock_file.assert_called_once_with(LEARNINGS_FILE, 'w', encoding='utf-8')
    mock_file().write.assert_called_once_with(new_content)

@patch('glob.glob')
@patch('builtins.open', new_callable=mock_open)
def test_update_md_file_success(mock_file, mock_glob, client_md):
    """Test successfully updating a specific MD file via POST."""
    # Simulate the file being valid
    mock_glob.return_value = [NOTES_FILE]
    new_content = "Updated Notes Content"
    response = client_md.post('/update_md_file', data={
        'filename': NOTES_FILE,
        'md_content': new_content
    })
    assert response.status_code == 302
    assert response.location == '/md_files'
    mock_glob.assert_called_once_with('*.md') # Security check uses glob
    mock_file.assert_called_once_with(NOTES_FILE, 'w', encoding='utf-8')
    mock_file().write.assert_called_once_with(new_content)

@patch('glob.glob')
@patch('builtins.open', new_callable=mock_open)
def test_update_md_file_invalid_filename(mock_file, mock_glob, client_md):
    """Test updating an MD file with a disallowed filename."""
    # Simulate the file NOT being in the allowed list
    mock_glob.return_value = [NOTES_FILE] # Only allow NOTES_FILE
    new_content = "Trying to write to wrong file"
    response = client_md.post('/update_md_file', data={
        'filename': '../etc/passwd', # Attempt traversal / invalid file
        'md_content': new_content
    })
    assert response.status_code == 302 # Still redirects
    assert response.location == '/md_files'
    mock_glob.assert_called_once_with('*.md')
    mock_file.assert_not_called() # Should not attempt to open/write
    # We can't easily check flash messages without more setup, but expect an error flash

def test_update_goals_missing_data(client_md):
    """Test POSTing to update goals with missing form data."""
    response = client_md.post('/update_goals', data={})
    assert response.status_code == 302 # Redirects back
    assert response.location == '/goals'
    # Expect error flash message

# Add similar tests for update_learnings and update_md_file missing data 