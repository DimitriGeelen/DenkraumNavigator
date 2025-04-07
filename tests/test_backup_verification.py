import os
import tempfile
import pytest

# Helper function simulating the core logic of the shell script's verification
def check_backup_file_status(filepath):
    """Checks if a file exists and is not empty. Returns True if valid, False otherwise."""
    if not os.path.isfile(filepath):
        print(f"Debug: Check failed - File not found: {filepath}")
        return False
    if os.path.getsize(filepath) == 0:
        print(f"Debug: Check failed - File is empty: {filepath}")
        return False
    print(f"Debug: Check successful - File exists and is not empty: {filepath}")
    return True

# Pytest fixture to create a temporary directory for tests
@pytest.fixture
def temp_backup_dir(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return backup_dir

# Test cases
def test_both_backups_valid(temp_backup_dir):
    """Tests the scenario where both DB and Code backups are present and valid."""
    db_path = temp_backup_dir / "db_commit_abc1234.db"
    code_path = temp_backup_dir / "code_commit_abc1234.zip"
    
    # Create valid dummy files
    db_path.write_text("dummy db content")
    code_path.write_text("dummy code content")
    
    db_status = check_backup_file_status(db_path)
    code_status = check_backup_file_status(code_path)
    
    assert db_status is True
    assert code_status is True
    # In the script, both True would lead to exit 0

def test_db_backup_missing(temp_backup_dir):
    """Tests the scenario where the DB backup file is missing."""
    db_path = temp_backup_dir / "db_commit_def4567.db"
    code_path = temp_backup_dir / "code_commit_def4567.zip"
    
    # Create only the code backup
    code_path.write_text("dummy code content")
    
    db_status = check_backup_file_status(db_path)
    code_status = check_backup_file_status(code_path)
    
    assert db_status is False
    assert code_status is True
    # In the script, False + True would lead to exit 1

def test_code_backup_missing(temp_backup_dir):
    """Tests the scenario where the Code backup file is missing."""
    db_path = temp_backup_dir / "db_commit_ghi7890.db"
    code_path = temp_backup_dir / "code_commit_ghi7890.zip"
    
    # Create only the db backup
    db_path.write_text("dummy db content")
    
    db_status = check_backup_file_status(db_path)
    code_status = check_backup_file_status(code_path)
    
    assert db_status is True
    assert code_status is False
    # In the script, True + False would lead to exit 1

def test_code_backup_empty(temp_backup_dir):
    """Tests the scenario where the Code backup file exists but is empty."""
    db_path = temp_backup_dir / "db_commit_jkl0123.db"
    code_path = temp_backup_dir / "code_commit_jkl0123.zip"
    
    # Create valid DB file and empty Code file
    db_path.write_text("dummy db content")
    code_path.touch() # Creates an empty file
    
    assert os.path.getsize(code_path) == 0 # Verify it's empty
    
    db_status = check_backup_file_status(db_path)
    code_status = check_backup_file_status(code_path)
    
    assert db_status is True
    assert code_status is False # Should fail because file is empty
    # In the script, True + False would lead to exit 1

def test_db_backup_empty(temp_backup_dir):
    """Tests the scenario where the DB backup file exists but is empty (less likely but possible)."""
    db_path = temp_backup_dir / "db_commit_mno4567.db"
    code_path = temp_backup_dir / "code_commit_mno4567.zip"
    
    # Create empty DB file and valid Code file
    db_path.touch() # Creates an empty file
    code_path.write_text("dummy code content")
    
    assert os.path.getsize(db_path) == 0 # Verify it's empty
    
    db_status = check_backup_file_status(db_path)
    code_status = check_backup_file_status(code_path)
    
    assert db_status is False # Should fail because file is empty
    assert code_status is True
    # In the script, False + True would lead to exit 1 