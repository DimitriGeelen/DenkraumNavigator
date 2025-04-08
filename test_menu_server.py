import os
from flask import Flask, render_template, g, request, current_app
import sqlite3
import io

# Assuming app.py is in the same directory or accessible via sys.path
try:
    # Import necessary components from the main app
    from app import (
        parse_menu_file, logger, MENU_FILE, GOALS_FILE, 
        get_db as main_get_db, 
        close_connection as main_close_connection, 
        query_db, 
        get_distinct_file_types, 
        get_distinct_years, 
        get_top_keywords,
        search_database
    )
    # Import the main app's config settings
    from app import app as main_app_for_config 
except ImportError as e:
    print(f"Error importing from app.py: {e}")
    # Provide default empty implementations or raise error
    logger = type('obj', (object,), {'info': print, 'debug': print, 'error': print, 'warning': print})()
    def parse_menu_file(filepath): return []
    def query_db(query, args=(), one=False): return []
    def get_distinct_file_types(): return []
    def get_distinct_years(): return []
    def get_top_keywords(limit=50): return []
    def search_database(**kwargs): return []
    MENU_FILE = 'menu.md' # Default fallback
    GOALS_FILE = 'PROJECT_GOALS.md'
    # Mock config if main app couldn't be imported
    main_app_for_config = type('obj', (object,), {
        'config': {'DATABASE': 'file_index.db', 'BACKUP_DIR': 'backups'}
    })()

# --- Minimal Flask App Setup ---
test_app = Flask(__name__, template_folder='templates') # Explicitly set template folder

# Copy config from main app
test_app.config.update(main_app_for_config.config)
logger.info(f"[Test Server] Copied config: {test_app.config}")

# Load menu globally at startup
test_main_menu = parse_menu_file(MENU_FILE)
logger.info(f"[Test Server] Main menu loaded at startup: {test_main_menu}")

# --- Database Handling (Adapted for test_app) ---

def get_db():
    """Opens a new database connection for the test app context."""
    # Uses test_app.config instead of current_app directly initially
    db_path = test_app.config['DATABASE']
    db = getattr(g, '_database', None)
    if db is None:
        if not os.path.exists(db_path):
             raise FileNotFoundError(f"[Test Server] Database file '{db_path}' not found.")
        db = g._database = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row 
    return db

@test_app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection at the end of the request for the test app."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
        logger.debug("[Test Server] Database connection closed.")

# --- Context Setup ---
@test_app.before_request
def before_request():
    """Add the globally loaded menu and DB path to the request context 'g'."""
    g.main_menu = test_main_menu
    # Ensure DB exists for get_db to work within request
    g.DATABASE = test_app.config['DATABASE'] 
    logger.debug(f"[Test Server] Added main_menu to g: {g.main_menu}")
    # logger.debug(f"[Test Server] g.DATABASE set to: {g.DATABASE}") # Optional debug

# --- Test Route mimicking main Index Page --- 
@test_app.route('/', methods=['GET', 'POST'])
def index(): # Function name MUST match endpoint in menu.md
    """Mimics the main index route structure."""
    logger.info(f"[Test Server Route: /] Accessed. Method: {request.method}")
    search_results = []
    search_terms = {}
    top_keywords = []
    distinct_types = []
    distinct_years = []

    # --- Fetch initial data for dropdowns/cloud ---
    try:
        distinct_types = get_distinct_file_types()
        distinct_years = get_distinct_years()
        top_keywords = get_top_keywords()
        logger.debug("[Test Server Route: /] Fetched distinct types, years, keywords.")
    except Exception as e:
        logger.error(f"[Test Server Route: /] Error fetching initial data: {e}")
        # Handle error appropriately, maybe flash a message
        pass

    if request.method == 'POST':
        logger.info("[Test Server Route: /] POST request received.")
        # Simplified search term extraction for now
        search_terms = {
            'filename': request.form.get('filename', '').strip(),
            'years': request.form.getlist('years'), # Get list for multi-select
            'file_types': request.form.getlist('type'), # Get list for multi-select
            'keywords': request.form.get('keywords', '').strip()
        }
        logger.debug(f"[Test Server Route: /] Search Terms: {search_terms}")
        
        # --- Uncomment search logic ---
        try:
            search_results = search_database(
                filename=search_terms['filename'],
                years=search_terms['years'], 
                file_types=search_terms['file_types'],
                keywords=search_terms['keywords']
            )
            logger.info(f"[Test Server Route: /] Search executed. Found {len(search_results)} results.")
        except Exception as e:
            logger.error(f"[Test Server Route: /] Error during search: {e}")
            # Handle error
            search_results = [] # Ensure it's an empty list on error
        # pass # Placeholder for POST logic (Remove this line)
        
    # Render a template that extends base.html
    # Use a distinct name like 'test_index_template.html' initially
    return render_template(
        'test_index_template.html', 
        results=search_results, 
        search_terms=search_terms,
        top_keywords=top_keywords,
        distinct_types=distinct_types,
        distinct_years=distinct_years,
        title="Test Search Page"
    )

# --- Other Dummy Routes (Keep for url_for) ---
@test_app.route('/dummy_browse')
def browse(): # Function name MUST match endpoint in menu.md
    return "Dummy Browse Page for url_for testing"

@test_app.route('/dummy_history')
def history(): # Function name MUST match endpoint in menu.md
    return "Dummy History Page for url_for testing"

@test_app.route('/dummy_goals')
def display_project_goals(): # Function name MUST match endpoint in menu.md
    return "Dummy Goals Page for url_for testing"

# --- Add Dummy Route for View File (used in results template) ---
@test_app.route('/dummy_view/<path:filepath>') # Need to accept the filepath argument
def view_file(filepath): # Function name MUST match endpoint used in url_for
    return f"Dummy View File page for path: {filepath}"

# Remove old /test_base route
# @test_app.route('/test_base')
# def test_base_page():
#     logger.info(f"[Test Server Route: /test_base] Rendering test_page_template.html (extends base.html)")
#     return render_template('test_page_template.html', title="Test Extending Base")

if __name__ == '__main__':
    port = 5001 # Use a different port
    print(f"[Test Server] Starting enhanced Flask test server for search page...")
    print(f"[Test Server] Access the test index page at http://127.0.0.1:{port}/")
    # Use debug=True for easier debugging of this test server
    test_app.run(debug=True, host='0.0.0.0', port=port) 