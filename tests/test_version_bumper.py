#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
import subprocess
from unittest.mock import patch, mock_open, MagicMock, call
import os
import zipfile

# Make the script accessible for import
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the script we want to test (assuming it can be imported)
# We might need to refactor version_bumper.py slightly if it's not import-friendly
# For now, let's assume we can import its main function or relevant parts.
# Let's try importing the module directly
import version_bumper

# Define constants used by the script
VERSION_FILE = version_bumper.VERSION_FILE
CHANGELOG_FILE = version_bumper.CHANGELOG_FILE
DB_FILENAME = version_bumper.DB_FILENAME
DB_ZIP_FILENAME = version_bumper.DB_ZIP_FILENAME

@pytest.fixture
def mock_dependencies(mocker):
    """Mocks external dependencies like subprocess calls and file system interactions."""
    mocks = {
        'run_command': mocker.patch('version_bumper.run_command'),
        'get_current_version': mocker.patch('version_bumper.get_current_version', return_value="1.0.0"),
        'get_latest_tag': mocker.patch('version_bumper.get_latest_tag', return_value="v1.0.0"),
        'get_commits_since_tag': mocker.patch('version_bumper.get_commits_since_tag', return_value="- Feat: New feature (abc123)"),
        'update_version_file': mocker.patch('version_bumper.update_version_file'),
        'update_changelog': mocker.patch('version_bumper.update_changelog'),
        'os_path_exists': mocker.patch('os.path.exists'),
        'zipfile_ZipFile': mocker.patch('zipfile.ZipFile'),
        'print': mocker.patch('builtins.print') # Mock print to check warnings
    }
    # Configure os.path.exists to return True for VERSION and CHANGELOG by default
    mocks['os_path_exists'].side_effect = lambda path: path in [VERSION_FILE, CHANGELOG_FILE]
    return mocks

def run_main_with_args(args_list):
    """Helper to run the main function with specific command line arguments."""
    with patch.object(sys, 'argv', ['version_bumper.py'] + args_list):
        version_bumper.main()

# --- Test Cases ---

def test_zip_created_and_staged_when_db_exists(mock_dependencies):
    """Test that file_index.zip is created and staged if file_index.db exists."""
    # Simulate file_index.db existing
    mock_dependencies['os_path_exists'].side_effect = lambda path: path in [VERSION_FILE, CHANGELOG_FILE, DB_FILENAME]
    
    # Simulate running with --minor flag
    run_main_with_args(['--minor'])
    
    # Assert ZipFile was called correctly
    mock_dependencies['zipfile_ZipFile'].assert_called_once_with(DB_ZIP_FILENAME, 'w', zipfile.ZIP_DEFLATED)
    # Assert the mock ZipFile's write method was called
    # Get the mock ZipFile instance created by the context manager
    mock_zip_instance = mock_dependencies['zipfile_ZipFile'].__enter__.return_value
    mock_zip_instance.write.assert_called_once_with(DB_FILENAME, arcname=DB_FILENAME)
    
    # Assert run_command was called for git add with the zip file
    expected_add_call = call(["git", "add", VERSION_FILE, CHANGELOG_FILE, DB_ZIP_FILENAME])
    # Check if this specific call is in the list of calls made to run_command
    assert expected_add_call in mock_dependencies['run_command'].call_args_list

def test_zip_not_staged_when_db_missing(mock_dependencies):
    """Test that file_index.zip is NOT created/staged if file_index.db is missing."""
    # Simulate file_index.db NOT existing (os.path.exists returns False for it)
    mock_dependencies['os_path_exists'].side_effect = lambda path: path in [VERSION_FILE, CHANGELOG_FILE]
    
    # Simulate running with --patch flag
    run_main_with_args(['--patch'])
    
    # Assert ZipFile was NOT called
    mock_dependencies['zipfile_ZipFile'].assert_not_called()
    
    # Assert run_command was called for git add WITHOUT the zip file
    expected_add_call = call(["git", "add", VERSION_FILE, CHANGELOG_FILE])
    assert expected_add_call in mock_dependencies['run_command'].call_args_list
    
    # Assert that a warning was printed
    mock_dependencies['print'].assert_any_call(f"Warning: Database file {DB_FILENAME} not found in root directory.", file=sys.stderr)

def test_zip_failure_warning_and_commit_proceeds(mock_dependencies):
    """Test that commit proceeds without zip if zipping fails, and warning is logged."""
    # Simulate file_index.db existing
    mock_dependencies['os_path_exists'].side_effect = lambda path: path in [VERSION_FILE, CHANGELOG_FILE, DB_FILENAME]
    # Simulate an error during ZipFile write
    mock_dependencies['zipfile_ZipFile'].__enter__.return_value.write.side_effect = Exception("Disk full")
    
    # Simulate running with --major flag
    run_main_with_args(['--major'])
    
    # Assert ZipFile was called
    mock_dependencies['zipfile_ZipFile'].assert_called_once_with(DB_ZIP_FILENAME, 'w', zipfile.ZIP_DEFLATED)
    
    # Assert run_command was called for git add WITHOUT the zip file
    expected_add_call = call(["git", "add", VERSION_FILE, CHANGELOG_FILE])
    assert expected_add_call in mock_dependencies['run_command'].call_args_list
    
    # Assert that warnings were printed
    mock_dependencies['print'].assert_any_call(f"Warning: Failed to create {DB_ZIP_FILENAME} from {DB_FILENAME}: Disk full", file=sys.stderr)
    mock_dependencies['print'].assert_any_call(f"Warning: Proceeding to commit without {DB_ZIP_FILENAME}.", file=sys.stderr)
    
    # Assert that the commit command was still called
    expected_commit_call = call(["git", "commit", "-m", "chore: Bump version to 2.0.0"]) # Calculated based on fixture
    assert expected_commit_call in mock_dependencies['run_command'].call_args_list 