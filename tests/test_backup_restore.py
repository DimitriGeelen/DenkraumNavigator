import os
import sqlite3
import time

def test_history_page_loads(client):
    """Test if the history page loads correctly."""
    response = client.get('/history')
    assert response.status_code == 200
    assert b"Version History" in response.data
    assert b"Manual Database Backups" in response.data

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