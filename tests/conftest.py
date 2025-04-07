import pytest
import os
import tempfile
import shutil
import sqlite3

# Assuming your Flask app instance is created in app.py
# You might need to adjust the import path based on your project structure
from app import app as flask_app

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    # Set the DATABASE path to a temporary file for the session
    # Use tmp_path_factory fixture which provides a session-scoped temp dir
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    backup_dir = tempfile.mkdtemp()
    
    flask_app.config.update({
        "TESTING": True,
        "DATABASE": db_path,
        "BACKUP_DIR": backup_dir,
        "SECRET_KEY": "testing", # Use a fixed secret key for testing sessions
        # Optional: Disable CSRF protection if you use WTForms/Flask-WTF
        # "WTF_CSRF_ENABLED": False 
    })

    # --- Minimal DB Setup for Tests ---
    # Create a minimal structure or copy a template DB if needed
    # This depends heavily on what your tests need. 
    # For now, just create the files table if it doesn't exist.
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT UNIQUE NOT NULL,
                        filename TEXT NOT NULL,
                        category_type TEXT,
                        category_year INTEGER,
                        summary TEXT,
                        keywords TEXT,
                        last_modified REAL
                    );""")
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Error setting up test database: {e}")
    # ---------------------------------
    
    yield flask_app
    
    # Clean up the temporary database and backup directory
    os.close(db_fd)
    os.unlink(db_path)
    shutil.rmtree(backup_dir)

@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture()
def db_path(app):
    """Provides the path to the temporary test database."""
    return app.config['DATABASE']

@pytest.fixture()
def backup_dir(app):
    """Provides the path to the temporary test backup directory."""
    return app.config['BACKUP_DIR']

@pytest.fixture(autouse=True)
def ensure_backup_dir_exists(backup_dir):
    """Ensure the temp backup dir exists before each test."""
    os.makedirs(backup_dir, exist_ok=True) 