#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
import os
from unittest.mock import patch, MagicMock
import tempfile # For creating temporary test files/dirs
import shutil

# Make the app accessible for testing
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app # Import the Flask app instance

# Define paths used in tests relative to a temporary directory
# We'll create these during test setup
INDEXED_ROOT_NAME = 'mock_archive'
BACKUPS_DIR_NAME = 'mock_backups'
DB_FILENAME = 'file_index.db'
CODE_FILENAME = 'app.py' # Example code file

@pytest.fixture
def client():
    """Create a Flask test client, setting up a temporary file structure."""
    # Create a temporary directory for the test run
    temp_dir = tempfile.mkdtemp()
    indexed_root = os.path.join(temp_dir, INDEXED_ROOT_NAME)
    backups_dir = os.path.join(temp_dir, BACKUPS_DIR_NAME)
    db_path = os.path.join(temp_dir, DB_FILENAME)
    code_path = os.path.join(temp_dir, CODE_FILENAME)
    
    os.makedirs(indexed_root, exist_ok=True)
    os.makedirs(backups_dir, exist_ok=True)
    
    # Create dummy files to test downloads
    # Indexed File
    test_file_rel_path = 'subdir/test_file.txt'
    test_file_abs_path = os.path.join(indexed_root, test_file_rel_path)
    os.makedirs(os.path.dirname(test_file_abs_path), exist_ok=True)
    with open(test_file_abs_path, 'w') as f:
        f.write("Indexed file content.")
        
    # Manual DB Backup
    manual_backup_name = 'file_index_20240101_120000.db'
    manual_backup_path = os.path.join(backups_dir, manual_backup_name)
    with open(manual_backup_path, 'w') as f:
        f.write("Manual backup content.")
        
    # Commit DB Backup
    commit_db_backup_name = 'commit_abc123.db' # Matches pattern in app route
    commit_db_backup_path = os.path.join(backups_dir, commit_db_backup_name)
    with open(commit_db_backup_path, 'w') as f:
        f.write("Commit DB backup content.")

    # Commit Code Backup
    commit_code_backup_name = 'commit_abc123.zip' # Matches pattern in app route
    commit_code_backup_path = os.path.join(backups_dir, commit_code_backup_name)
    with open(commit_code_backup_path, 'w') as f:
        f.write("Commit code backup content.")

    # Create dummy current DB and code file (needed for package download)
    with open(db_path, 'w') as f: f.write("Current DB")
    with open(code_path, 'w') as f: f.write("Current Code")

    # Configure the app for testing
    app.config['TESTING'] = True
    # Point config to our temporary directories/files
    # IMPORTANT: Need to ensure app uses these config values. Test setup might need adjustment.
    # For now, we assume app.py reads these or uses defaults we can override.
    # Let's use patch.dict on app.config *within* the tests where needed, or set here if sure.
    app.config['INDEXED_ROOT_DIR'] = indexed_root
    app.config['BACKUP_DIR'] = backups_dir
    app.config['DATABASE'] = db_path # For download_package

    with app.test_client() as client:
        yield client # Provide the test client to the test functions

    # Teardown: Remove the temporary directory
    shutil.rmtree(temp_dir)

# --- Test Cases ---

# /download/<path:file_path>
def test_download_file_success(client):
    """Test successful download of a file within the indexed root."""
    # Note: Path is relative to INDEXED_ROOT_DIR in the URL
    response = client.get('/download/subdir/test_file.txt')
    assert response.status_code == 200
    assert response.headers['Content-Disposition'] == 'attachment; filename=test_file.txt'
    assert b'Indexed file content.' in response.data

def test_download_file_not_found(client):
    """Test downloading a non-existent file."""
    response = client.get('/download/subdir/nonexistent.txt')
    assert response.status_code == 404

def test_download_file_traversal_attempt(client):
    """Test attempting to download a file outside the indexed root."""
    # Construct path trying to go up from indexed root
    # Need enough '../' to escape the temp dir structure
    response = client.get('/download/../../../../etc/passwd') 
    assert response.status_code == 403 # Forbidden

# /download_backup/<filename>
def test_download_backup_success(client):
    """Test successful download of a manual DB backup."""
    response = client.get('/download_backup/file_index_20240101_120000.db')
    assert response.status_code == 200
    assert response.headers['Content-Disposition'] == 'attachment; filename=file_index_20240101_120000.db'
    assert b'Manual backup content.' in response.data

def test_download_backup_not_found(client):
    """Test downloading non-existent backup."""
    response = client.get('/download_backup/nonexistent.db')
    assert response.status_code == 404

def test_download_backup_traversal_attempt(client):
    """Test directory traversal attempt for backups."""
    response = client.get('/download_backup/../test_file.txt') # Try to access file outside backup dir
    assert response.status_code == 404

# /download_commit_package/<commit_hash>
# Note: This route in app.py actually zips files on the fly.
# Testing it properly requires mocking os.path.exists, glob.glob, zipfile.ZipFile etc.
# We already have an integration test in test_backup_restore.py for the happy path.
# Adding more detailed unit tests here would be complex due to mocking.
# Let's skip adding more tests for this specific route here, relying on existing integration test.

# /download_code
def test_download_code_success(client):
    """Test downloading the current code zip."""
    # This route also creates a zip on the fly. We mostly check if it runs.
    response = client.get('/download_code')
    assert response.status_code == 200
    assert response.mimetype == 'application/zip'
    assert 'attachment; filename=dol_data_archiver_code_' in response.headers['Content-Disposition']
    # We could inspect the zip content but that gets complex quickly

# /download_package
def test_download_package_success(client):
    """Test downloading the current package (code + db) zip."""
    # Similar to download_code, creates zip on the fly.
    response = client.get('/download_package')
    assert response.status_code == 200
    assert response.mimetype == 'application/zip'
    assert 'attachment; filename=dol_data_archiver_package_' in response.headers['Content-Disposition'] 