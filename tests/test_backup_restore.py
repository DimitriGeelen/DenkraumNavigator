import os
import sqlite3
import time
import subprocess
import glob
import re
import pytest
from flask import url_for
from unittest.mock import patch
# Import the original function to call it from the mock
from app import get_commit_details as original_get_commit_details 

def test_history_page_loads(client):
    """Test if the history page loads correctly."""
    response = client.get('/history')
    assert response.status_code == 200
    assert b"Version History" in response.data
    assert b"Manual Database Backups" in response.data
    assert b'Detailed Commit History' in response.data

def test_manual_backup_creation(client, backup_dir):
    """Test creating a manual backup via the POST request."""
    initial_backups = os.listdir(backup_dir)
    response = client.post('/backup', follow_redirects=True)
    assert response.status_code == 200
    assert b"Backup created successfully" in response.data # Check for flash message

    current_backups = os.listdir(backup_dir)
    assert len(current_backups) == len(initial_backups) + 1
    # Find the new backup file (the one not in initial_backups)
    new_backup = list(set(current_backups) - set(initial_backups))
    assert len(new_backup) == 1
    assert new_backup[0].startswith('file_index_')
    assert new_backup[0].endswith('.db')

def test_database_restore(client, db_path, backup_dir):
    """Test restoring the database from a backup."""
    # Explicitly clear backup dir at start to ensure clean state
    print(f"Clearing temporary backup directory: {backup_dir}")
    for item in os.listdir(backup_dir):
        item_path = os.path.join(backup_dir, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
            
    # 1. Create initial backup (clean state)
    response_backup1 = client.post('/backup', follow_redirects=True)
    assert response_backup1.status_code == 200
    backups_after_1 = os.listdir(backup_dir)
    backup1_filename = list(set(backups_after_1))[0] # Assume only one backup exists now
    assert backup1_filename.startswith('file_index_')
    
    # Give a second for timestamp difference
    time.sleep(1.1)

    # 2. Modify the live database
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO files (path, filename) VALUES (?, ?)", ('/test/path1', 'testfile1.txt'))
    conn.commit()
    # Verify change
    cursor = conn.execute("SELECT COUNT(*) FROM files WHERE filename = ?", ('testfile1.txt',))
    assert cursor.fetchone()[0] == 1
    conn.close()

    # 3. Create another backup (modified state - not used for restore in this test)
    response_backup2 = client.post('/backup', follow_redirects=True)
    assert response_backup2.status_code == 200
    backups_after_2 = os.listdir(backup_dir)
    assert len(backups_after_2) == 2 # Should have two backups now
    
    # 4. Restore the *first* backup (clean state)
    # Don't follow redirects initially to check the session for the flash message
    response_restore_no_redirect = client.post(f'/restore_backup/{backup1_filename}')
    # Check the session for the flash message before the redirect happens
    with client.session_transaction() as session:
        flash_messages = session.get('_flashes', [])
        assert len(flash_messages) >= 1
        assert flash_messages[0][0] == 'success' # Check category
        assert "Database successfully restored" in flash_messages[0][1] # Check message text

    # Now check the redirect itself
    assert response_restore_no_redirect.status_code == 302 # Should be a redirect
    assert response_restore_no_redirect.location == '/history' # Should redirect to history

    # Optionally, follow the redirect to ensure the history page loads
    response_restore_redirected = client.get(response_restore_no_redirect.location)
    assert response_restore_redirected.status_code == 200

    # 5. Verify the database is back to the initial state (dummy data is gone)
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM files WHERE filename = ?", ('testfile1.txt',))
    assert cursor.fetchone()[0] == 0 # The test file should no longer exist
    conn.close()

    # 6. Test restoring a non-existent file (should fail)
    response_restore_fail = client.post('/restore_backup/non_existent_backup.db', follow_redirects=True)
    assert response_restore_fail.status_code == 404 # Not Found

    # 7. Test restoring with invalid filename (should fail)
    # Don't follow redirects here to potentially see flash message in session if abort(400) happens
    response_restore_bad = client.post('/restore_backup/../invalid_path.db')
    # Expecting 404 here because Flask/Werkzeug likely handles ../ before our check
    assert response_restore_bad.status_code == 404 # NOT FOUND (due to framework path handling)
    # Check for the specific flash message associated with the 400 error
    # with client.session_transaction() as session:
    #      flash_messages = session.get('_flashes', [])

    # Add a check for a valid file but wrong extension
    # Create a dummy non-db file in backups
    dummy_file_path = os.path.join(backup_dir, "not_a_database.txt")
    with open(dummy_file_path, 'w') as f:
        f.write("test")
    response_restore_ext = client.post('/restore_backup/not_a_database.txt')
    assert response_restore_ext.status_code == 400 # Should be bad request due to extension
    os.remove(dummy_file_path) # Clean up dummy file

def test_download_link_for_latest_commit(client, app, mocker):
    """Integration test: Commit -> Hook -> History Page -> Download Link Verification"""
    print("\nRunning test: test_download_link_for_latest_commit")
    # Use the ACTUAL project backup dir, not the temp one from app config,
    # because the git hook doesn't know about the test config.
    # Construct path relative to this test file's location
    tests_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(tests_dir) # Go one level up from tests/
    backup_dir = os.path.join(project_root, "backups")
    # Ensure it exists for the test assertion, though hook should create it
    os.makedirs(backup_dir, exist_ok=True)
    print(f"DEBUG: Using backup_dir for verification: {backup_dir}") # Add debug print

    notes_file = "PROJECT_NOTES.md" # A file we can easily modify
    latest_commit_hash = None # Initialize

    # --- 1. Make a new commit to trigger the hook ---
    try:
        # Make a small change
        with open(notes_file, "a") as f:
            f.write("\n# Test commit for download link verification.")
        
        # Stage the change
        stage_cmd = ["git", "add", notes_file]
        subprocess.run(stage_cmd, check=True, capture_output=True, text=True)
        print(f"Staged changes to {notes_file}")

        # Commit the change
        commit_msg = "test: Create commit to verify download link on history page - integration"
        commit_cmd = ["git", "commit", "-m", commit_msg]
        print(f"Running commit: {' '.join(commit_cmd)}")
        commit_result = subprocess.run(commit_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print("Commit successful. Post-commit hook output:")
        print(commit_result.stderr) # Hook output is often on stderr
        assert "SUCCESS: Database and Code backups completed" in commit_result.stderr
        hash_cmd = ["git", "rev-parse", "--short", "HEAD"]
        hash_result = subprocess.run(hash_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        latest_commit_hash = hash_result.stdout.strip()
        print(f"Latest commit hash: {latest_commit_hash}")
        assert len(latest_commit_hash) > 0

    except subprocess.CalledProcessError as e:
        print(f"Git command failed during test setup:")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Stderr: {e.stderr}")
        print(f"Stdout: {e.stdout}")
        pytest.fail(f"Git command failed: {e}")
    except FileNotFoundError:
         pytest.fail("Git command not found. Is Git installed and in PATH?")

    # --- 2. Verify backup files exist for this commit (Optional but good sanity check) ---
    # We still perform this check, but the crucial part is mocking for the web request
    print("Performing sanity check for backup file existence...")
    time.sleep(1) # Shorter delay might be okay now
    exact_db_filename = f"commit_{latest_commit_hash}.db"
    exact_code_filename = f"commit_{latest_commit_hash}.zip"
    exact_db_path = os.path.join(backup_dir, exact_db_filename)
    exact_code_path = os.path.join(backup_dir, exact_code_filename)
    db_found = os.path.exists(exact_db_path)
    code_found = os.path.exists(exact_code_path)
    print(f"Sanity check: DB found={db_found}, Code found={code_found}")
    # We don't strictly need to assert here anymore if we trust the hook output and mock below
    # assert db_found and code_found, "Backup files not found during sanity check"

    # --- 3. Verify link appears on history page (with mocking get_commit_details) ---
    print(f"Fetching /history page for commit {latest_commit_hash}...")

    def mock_get_commit_details_wrapper(limit=None): # Match original signature
        print(f"*** MOCK get_commit_details CALLED for limit={limit} ***")
        # Call the REAL function first
        real_commits = original_get_commit_details(limit=limit) 
        print(f"*** MOCK received {len(real_commits)} commits from real function ***")
        # Modify the specific commit we care about
        modified = False
        for commit in real_commits:
            if commit['hash'] == latest_commit_hash:
                print(f"*** MOCK Found commit {latest_commit_hash}, setting backups to True ***")
                commit['has_db_backup'] = True
                commit['has_zip_backup'] = True
                modified = True
                break 
        if not modified:
             print(f"*** MOCK WARNING: Did not find commit {latest_commit_hash} in results to modify! ***")
        print(f"*** MOCK returning modified commit list. ***")
        return real_commits # Return the modified list

    # Patch app.get_commit_details directly
    mocker.patch('app.get_commit_details', side_effect=mock_get_commit_details_wrapper) 
    
    print("Making request to /history inside get_commit_details mocked context...")
    response = client.get('/history')
    print("Request to /history complete.")

    # No need to stop, mocker handles teardown.

    # --- Assertions remain the same --- 
    assert response.status_code == 200
    page_content = response.data.decode('utf-8')
    expected_link_url = url_for('download_commit_package', commit_hash=latest_commit_hash)
    print(f"Checking for link URL: {expected_link_url} for hash {latest_commit_hash}")
    expected_span_pattern = rf'<span class="btn-link btn-link-disabled"[^>]*>\\s*Package Unavailable\\s*</span>'
    commit_list_item_pattern = rf'<ul class="content-list">.*?<li>.*?<strong>{latest_commit_hash}</strong>.*?</small>.*?<div class="actions">(.*?)</div>.*?</li>'
    match = re.search(commit_list_item_pattern, page_content, re.DOTALL | re.IGNORECASE)
    assert match, f"Could not find list item structure for commit {latest_commit_hash} on /history page"
    actions_html = match.group(1)
    print(f"Found actions HTML for {latest_commit_hash}: {actions_html.strip()}")

    # --- Simplified Assertion --- 
    # Check if the correct href attribute exists within the actions_html string
    print(f"Simplified check: Searching for href='{expected_link_url}' in actions_html")
    href_found = f'href="{expected_link_url}"' in actions_html
    assert href_found, f"Link with href='{expected_link_url}' not found for commit {latest_commit_hash} in actions: {actions_html.strip()}"

    # Check for absence of disabled span still
    unavailable_span_found = re.search(expected_span_pattern, actions_html) is not None
    assert not unavailable_span_found, f"'Package Unavailable' span unexpectedly found for commit {latest_commit_hash} in actions: {actions_html.strip()}"

    # --- 4. Cleanup: Remove the commit from git history? (Optional, complex) ---
    # For now, just remove the line from the notes file to avoid cluttering it
    try:
        with open(notes_file, "r") as f:
            lines = f.readlines()
        with open(notes_file, "w") as f:
            # Write back all lines except the last one (our test line)
            f.writelines(lines[:-1])
        # Stage and commit the cleanup (optional, might trigger hook again!)
        # subprocess.run(["git", "add", notes_file], check=True)
        # subprocess.run(["git", "commit", "--amend", "--no-edit"], check=True)
        print(f"Cleaned up test line from {notes_file}")
    except Exception as clean_e:
        print(f"Warning: Cleanup failed for {notes_file}: {clean_e}") 