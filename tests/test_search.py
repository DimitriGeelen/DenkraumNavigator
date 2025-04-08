import pytest
import sqlite3
import os

# Make the app accessible for testing
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app # Import the Flask app instance

DB_FILENAME = 'test_search.db' # Use a dedicated test DB filename

# Define the database schema (copied from indexer.py)
DB_SCHEMA = '''
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT,
    size_bytes INTEGER,
    last_modified REAL, -- Store as Unix timestamp
    category_year INTEGER,
    category_type TEXT,
    category_event TEXT DEFAULT 'Unknown', -- Placeholder with default
    category_meeting TEXT DEFAULT 'Unknown', -- Placeholder with default
    summary TEXT,
    keywords TEXT, -- Store as comma-separated string
    processing_status TEXT DEFAULT 'Pending', -- Pending, Success, Failed
    processing_error TEXT -- Store error message if processing failed
);
CREATE INDEX IF NOT EXISTS idx_path ON files (path);
CREATE INDEX IF NOT EXISTS idx_filename ON files (filename);
CREATE INDEX IF NOT EXISTS idx_type ON files (category_type);
CREATE INDEX IF NOT EXISTS idx_year ON files (category_year);
CREATE INDEX IF NOT EXISTS idx_status ON files (processing_status);
'''

@pytest.fixture
def client_search(tmp_path): # Use pytest's tmp_path fixture
    """Creates a Flask test client and a temporary, populated search database."""
    db_path = tmp_path / DB_FILENAME
    conn = sqlite3.connect(db_path)
    # Create the table structure
    conn.executescript(DB_SCHEMA)
    # Insert sample data
    sample_data = [
        ('/path/to/file1.txt', 'file1.txt', '.txt', 100, 2023, 'Text', 'Event A', 'Meeting 1', 'Summary 1', 'keyword1,keyword2'),
        ('/path/to/document.docx', 'document.docx', '.docx', 200, 2024, 'Word Document', 'Event B', 'Meeting 2', 'Summary 2', 'keyword2,keyword3'),
        ('/path/other/image.jpg', 'image.jpg', '.jpg', 300, 2023, 'Image', 'Event A', 'Meeting 3', 'Summary 3', 'keyword1,keyword4')
    ]
    conn.executemany("""
        INSERT INTO files (path, filename, extension, size_bytes, category_year, category_type, category_event, category_meeting, summary, keywords) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_data)
    conn.commit()
    conn.close()
    
    # Configure app to use this test database
    app.config['TESTING'] = True
    app.config['DATABASE'] = str(db_path) # Use the path to the temp db

    with app.test_client() as client:
        yield client
    
    # Teardown is handled by tmp_path fixture

def test_index_page_loads(client_search):
    """Test that the index page loads successfully."""
    response = client_search.get('/')
    assert response.status_code == 200
    assert b'DenkraumNavigator Archive Search' in response.data

def test_search_by_filename(client_search):
    """Test searching by filename."""
    response = client_search.post('/', data={'filename': 'file1'})
    assert response.status_code == 200
    assert b'file1.txt' in response.data
    assert b'document.docx' not in response.data

def test_search_by_keyword(client_search):
    """Test searching by keyword."""
    response = client_search.post('/', data={'keywords': 'keyword2'})
    assert response.status_code == 200
    assert b'file1.txt' in response.data
    assert b'document.docx' in response.data
    assert b'image.jpg' not in response.data
    # Test cloud link click (GET request)
    response = client_search.get('/?keywords=keyword4')
    assert response.status_code == 200
    assert b'image.jpg' in response.data
    assert b'file1.txt' not in response.data

def test_search_by_type(client_search):
    """Test searching by file type."""
    response = client_search.post('/', data={'type': 'Text'})
    assert response.status_code == 200
    assert b'file1.txt' in response.data
    assert b'document.docx' not in response.data

def test_search_by_year(client_search):
    """Test searching by year."""
    response = client_search.post('/', data={'year': '2024'})
    assert response.status_code == 200
    assert b'document.docx' in response.data
    assert b'file1.txt' not in response.data

def test_search_by_multiple_criteria(client_search):
    """Test searching with multiple filters."""
    response = client_search.post('/', data={'filename': 'file', 'year': '2023', 'type': 'Text'})
    assert response.status_code == 200
    assert b'file1.txt' in response.data
    assert b'image.jpg' not in response.data

def test_search_no_results(client_search):
    """Test search returning no results."""
    response = client_search.post('/', data={'filename': 'nonexistent'})
    assert response.status_code == 200
    assert b'No files found matching your criteria.' in response.data 