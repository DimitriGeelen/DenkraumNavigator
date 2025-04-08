#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
import os
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# Make the app accessible for testing
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app # Import the Flask app instance

# Define paths used in tests relative to a temporary directory
INDEXED_ROOT_NAME = 'mock_archive'

@pytest.fixture
def client_browse(): # Renamed fixture to avoid potential conflicts
    """Create a Flask test client, setting up a temporary archive structure."""
    temp_dir = tempfile.mkdtemp()
    indexed_root = os.path.join(temp_dir, INDEXED_ROOT_NAME)
    
    # Create directory structure
    os.makedirs(os.path.join(indexed_root, 'subdir1'), exist_ok=True)
    os.makedirs(os.path.join(indexed_root, 'subdir2_empty'), exist_ok=True)
    
    # Create dummy files
    with open(os.path.join(indexed_root, 'root_file.txt'), 'w') as f:
        f.write("Root file.")
    with open(os.path.join(indexed_root, 'subdir1', 'sub_file1.pdf'), 'w') as f:
        f.write("Sub file 1.")
    with open(os.path.join(indexed_root, 'subdir1', 'sub_file2.docx'), 'w') as f:
        f.write("Sub file 2.")
        
    # Configure the app for testing
    app.config['TESTING'] = True
    app.config['INDEXED_ROOT_DIR'] = indexed_root
    # Mock the database query to avoid needing a real DB for browse info
    # This mock assumes any file path asked for exists in the DB (simplification)
    # A more complex mock could return specific data or None
    mock_query_db = MagicMock(return_value=MagicMock())
    
    with patch('app.query_db', mock_query_db): # Patch query_db used within the browse route
        with app.test_client() as client:
            yield client

    # Teardown: Remove the temporary directory
    shutil.rmtree(temp_dir)

# --- Test Cases ---

def test_browse_root_success(client_browse):
    """Test browsing the root directory."""
    response = client_browse.get('/browse/')
    assert response.status_code == 200
    # Check for expected directories and files (simple substring check)
    assert b'subdir1' in response.data
    assert b'subdir2_empty' in response.data
    assert b'root_file.txt' in response.data
    # Check breadcrumbs
    assert b'Archive Root' in response.data 
    assert b'/' not in response.data # Root should not have slash separator in breadcrumb

def test_browse_subdir_success(client_browse):
    """Test browsing a subdirectory."""
    response = client_browse.get('/browse/subdir1/') # Note trailing slash handled by Flask
    assert response.status_code == 200
    # Check for expected files
    assert b'sub_file1.pdf' in response.data
    assert b'sub_file2.docx' in response.data
    # Check these are NOT listed
    assert b'root_file.txt' not in response.data
    assert b'subdir2_empty' not in response.data
    # Check breadcrumbs
    assert b'Archive Root' in response.data
    assert b'subdir1' in response.data
    assert b'/' in response.data # Should have separator now

def test_browse_empty_dir(client_browse):
    """Test browsing an empty subdirectory."""
    response = client_browse.get('/browse/subdir2_empty/')
    assert response.status_code == 200
    assert b'This directory is empty.' in response.data
    # Check breadcrumbs
    assert b'Archive Root' in response.data
    assert b'subdir2_empty' in response.data

def test_browse_nonexistent_dir(client_browse):
    """Test browsing a non-existent path."""
    response = client_browse.get('/browse/does_not_exist/')
    assert response.status_code == 404

def test_browse_traversal_attempt(client_browse):
    """Test directory traversal attempt."""
    response = client_browse.get('/browse/../') # Try to go above root
    assert response.status_code == 403 # Forbidden by check in route
    response = client_browse.get('/browse/%2e%2e/') # URL encoded
    assert response.status_code == 403 # Forbidden

# Test floating navigation bar elements (Added in previous steps)
def test_browse_root_has_nav_bar(client_browse):
    """Check if the floating nav bar is present on the root browse page."""
    response = client_browse.get('/browse/')
    assert response.status_code == 200
    assert b'page-nav-links' in response.data # Check for the nav container
    assert b'#directories' in response.data
    assert b'#files' in response.data

def test_browse_subdir_has_nav_bar(client_browse):
    """Check if the floating nav bar is present on a subdirectory browse page."""
    response = client_browse.get('/browse/subdir1/')
    assert response.status_code == 200
    assert b'page-nav-links' in response.data # Check for the nav container
    # In subdir1, only files exist in our test setup
    assert b'#directories' not in response.data
    assert b'#files' in response.data 