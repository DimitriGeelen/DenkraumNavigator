import pytest
import sqlite3

# Sample data to insert for testing search
TEST_FILES_DATA = [
    # path, filename, category_type, category_year, summary, keywords, last_modified
    ('/archive/doc1.txt', 'doc1.txt', 'TEXT', 2023, 'Summary about apples.', 'apple,fruit,text', 1678886400), 
    ('/archive/doc2.pdf', 'doc2.pdf', 'PDF', 2023, 'A document about bananas.', 'banana,fruit,pdf', 1678886401), 
    ('/archive/img1.jpg', 'img1.jpg', 'IMAGE', 2024, 'Picture of cherries.', 'cherry,fruit,image', 1710508800), 
    ('/archive/report.pdf', 'report.pdf', 'PDF', 2024, 'Annual report mentioning apples and cherries.', 'report,apple,cherry', 1710508801), 
    ('/archive/old_doc.txt', 'old_doc.txt', 'TEXT', 2022, 'Very old text file.', 'old,document', 1647350400), 
]

@pytest.fixture(autouse=True)
def setup_search_db(db_path):
    """Fixture to populate the test database with search data before each test."""
    conn = sqlite3.connect(db_path)
    # Clear existing data first to ensure isolation
    conn.execute("DELETE FROM files;") 
    # Insert test data
    conn.executemany("""INSERT INTO files 
                        (path, filename, category_type, category_year, summary, keywords, last_modified)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""", TEST_FILES_DATA)
    conn.commit()
    conn.close()
    yield # Test runs here
    # Teardown (optional, as db is temporary anyway, but good practice)
    # conn = sqlite3.connect(db_path)
    # conn.execute("DELETE FROM files;")
    # conn.commit()
    # conn.close()

def test_index_page_loads(client):
    """Test loading the index/search page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"<title>DenkraumNavigator Archive Search</title>" in response.data
    assert b"Search" in response.data # Check for form presence (submit button text)

def test_search_by_filename(client):
    """Test searching by filename."""
    response = client.post('/', data={'filename': 'doc1'})
    assert response.status_code == 200
    assert b"doc1.txt" in response.data
    assert b"doc2.pdf" not in response.data
    assert b"report.pdf" not in response.data

def test_search_by_keyword(client):
    """Test searching by keyword (in keywords, summary, or filename)."""
    response = client.post('/', data={'keywords': 'apple'})
    assert response.status_code == 200
    assert b"doc1.txt" in response.data # Matches keyword/summary
    assert b"report.pdf" in response.data # Matches summary
    assert b"doc2.pdf" not in response.data

def test_search_by_type(client):
    """Test searching by file type."""
    response = client.post('/', data={'type': 'PDF'})
    assert response.status_code == 200
    assert b"doc2.pdf" in response.data
    assert b"report.pdf" in response.data
    assert b"doc1.txt" not in response.data

def test_search_by_year(client):
    """Test searching by year."""
    response = client.post('/', data={'year': '2024'})
    assert response.status_code == 200
    assert b"img1.jpg" in response.data
    assert b"report.pdf" in response.data
    assert b"doc1.txt" not in response.data

def test_search_by_multiple_criteria(client):
    """Test searching with multiple criteria combined (AND)."""
    # PDF from 2024 containing 'report'
    response = client.post('/', data={
        'filename': 'report', 
        'year': '2024', 
        'type': 'PDF'
    })
    assert response.status_code == 200
    assert b"report.pdf" in response.data
    assert b"doc1.txt" not in response.data
    assert b"doc2.pdf" not in response.data
    assert b"img1.jpg" not in response.data

def test_search_no_results(client):
    """Test a search that should yield no results."""
    response = client.post('/', data={'filename': 'nonexistentfile'})
    assert response.status_code == 200
    # Check for the 'no results' message or absence of result elements
    # This depends on how your template indicates no results.
    # Assuming no specific message, just check known results aren't present
    assert b"doc1.txt" not in response.data
    assert b"report.pdf" not in response.data 
    # Check if the 'No results found' text is present (add this to your template if needed)
    # assert b"No results found matching your criteria." in response.data 