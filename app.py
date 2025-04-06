import sqlite3
import os
import subprocess # For running git log
import zipfile
import io
import datetime # For timestamp in zip filename
import shutil # Import shutil for file copying
from flask import Flask, render_template, request, g, send_file, abort, flash, redirect, url_for # Add flash, redirect, url_for
from collections import Counter
import math # For tag cloud scaling
import logging

DATABASE = 'file_index.db'
# IMPORTANT: Define the root directory that contains the indexed files for security
# This should be the directory you passed to indexer.py (e.g., /dol-data-archive2)
INDEXED_ROOT_DIR = "/dol-data-archive2"
BACKUP_DIR = "backups"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) # Needed for flash messages, etc.

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    db = getattr(g, '_database', None)
    if db is None:
        if not os.path.exists(DATABASE):
             # In a real app, handle this more gracefully, maybe redirect to an error page
             raise FileNotFoundError(f"Database file '{DATABASE}' not found. Run indexer first.")
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # Return rows as dictionary-like objects
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Helper function to query the database."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def get_distinct_file_types():
    """Queries the database for distinct, non-empty file types."""
    # Order them for consistent display
    query = "SELECT DISTINCT category_type FROM files WHERE category_type IS NOT NULL AND category_type != '' ORDER BY category_type"
    rows = query_db(query)
    return [row['category_type'] for row in rows]

def get_distinct_years():
    """Queries the database for distinct years, ordered descending."""
    query = "SELECT DISTINCT category_year FROM files WHERE category_year IS NOT NULL ORDER BY category_year DESC"
    rows = query_db(query)
    # Keep as int for comparison
    return [row['category_year'] for row in rows]

def search_database(filename=None, years=None, file_types=None, keywords=None):
    """Performs the search query based on provided criteria."""
    # Renamed year to years (plural)
    base_query = "SELECT path, filename, category_type, category_year, summary, keywords FROM files WHERE 1=1"
    conditions = []
    params = []

    if filename:
        conditions.append("filename LIKE ?")
        params.append(f"%{filename}%")

    # Handle single or multiple years
    if years: # Check if the list is not empty
        try:
            # Ensure years are integers
            year_ints = [int(y) for y in years if y] 
            if year_ints:
                placeholders = ', '.join('?' * len(year_ints))
                conditions.append(f"category_year IN ({placeholders})")
                params.extend(year_ints)
        except ValueError:
            # Handle invalid year input gracefully (e.g., ignore or show error)
            print(f"Warning: Invalid year value encountered in {years}") # Log warning
            pass 

    # Handle single or multiple file types
    if file_types: # Check if the list is not empty
        # Ensure we have a list, even if only one was passed initially
        if isinstance(file_types, str):
            file_types = [file_types]
        
        # Create placeholders for the IN clause
        placeholders = ', '.join('?' * len(file_types))
        conditions.append(f"category_type IN ({placeholders})")
        params.extend(file_types)

    if keywords:
        keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        keyword_conditions = []
        for kw in keyword_list:
            keyword_conditions.append("(keywords LIKE ? OR summary LIKE ? OR filename LIKE ?)") # Also check filename
            params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
        if keyword_conditions:
            conditions.append(f"({' AND '.join(keyword_conditions)})")

    # Only execute query if there are actual conditions beyond WHERE 1=1
    if conditions:
        sql_query = f"{base_query} AND {' AND '.join(conditions)} ORDER BY last_modified DESC" # Order by date
        # print(f"DEBUG SQL: {sql_query}") # Uncomment for debugging
        # print(f"DEBUG PARAMS: {params}")
        try:
             results = query_db(sql_query, params)
             return results
        except sqlite3.Error as e:
            print(f"Database search error: {e}") # Log this properly in a real app
            return [] # Return empty list on error
    else:
        # Maybe return recent files or show a message?
        return []

def get_top_keywords(limit=50):
    """Fetches all keywords from the DB and returns the most frequent ones."""
    all_keywords_str = query_db("SELECT keywords FROM files WHERE keywords IS NOT NULL AND keywords != ''")
    print(f"DEBUG [get_top_keywords]: Found {len(all_keywords_str)} rows with keywords.") # Debug
    
    keyword_counts = Counter()
    for i, row in enumerate(all_keywords_str):
        # Keywords are stored comma-separated
        if row['keywords']:
            keywords = row['keywords'].split(',')
            # if i < 5: print(f"DEBUG [get_top_keywords]: Row {i} keywords: {keywords}") # Debug first 5 rows
            keyword_counts.update(kw.strip() for kw in keywords if kw.strip()) # Count non-empty keywords
        
    # Get the most common keywords and their counts
    top_keywords = keyword_counts.most_common(limit)
    print(f"DEBUG [get_top_keywords]: Top {limit} raw keyword counts (first 5): {top_keywords[:5]}") # Debug
    
    # Add scaling factor for font size (optional, adjust as needed)
    if top_keywords:
        # max_count = top_keywords[0][1]  # Removed F841
        # min_count = top_keywords[-1][1]  # Removed F841
        # Apply log scaling to prevent huge differences, avoid log(0 or 1)
        log_min = 1 # To avoid log(0)
        log_max = math.log(top_keywords[0][1] + log_min) if top_keywords else 1 # Avoid error on empty
        log_range = log_max - math.log(top_keywords[-1][1] + log_min) if len(top_keywords) > 1 and top_keywords[-1][1] > 0 else 1 # Avoid div by zero or log(0)
        log_range = max(log_range, 1) # Ensure range is at least 1
        
        final_keywords = []
        for kw, count in top_keywords:
            if log_range > 0:
                # Scale font size from, say, 1 (min) to 4 (max) relative units
                font_scale = 1 + 3 * (math.log(count + log_min) - log_min) / log_range 
            else:
                font_scale = 2 # Default size if all counts are the same
            final_keywords.append({'text': kw, 'weight': count, 'font_scale': font_scale})
        # print(f"DEBUG [get_top_keywords]: Final scaled keywords (first 5): {final_keywords[:5]}") # Debug
        return final_keywords
    else:
        print("DEBUG [get_top_keywords]: No top keywords found after counting.") # Debug
        return []

def create_backup():
    """Creates a timestamped backup of the database file."""
    if not os.path.exists(DATABASE):
        logger.error("Database file not found, cannot create backup.")
        return None

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"file_index_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        shutil.copy2(DATABASE, backup_path) # copy2 preserves metadata
        logger.info(f"Database backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        return None

@app.route('/backup', methods=['POST'])
def backup_now():
    """Route to trigger a manual database backup."""
    backup_file = create_backup()
    if backup_file:
        flash(f"Backup created successfully: {os.path.basename(backup_file)}", 'success')
    else:
        flash("Failed to create backup.", 'error')
    # Redirect back to the history page (or wherever appropriate)
    return redirect(url_for('history'))

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    search_terms = {}
    selected_types = []
    selected_years = [] # Use list for years now
    
    # Check both POST form data and GET query parameters
    if request.method == 'POST':
        # Get data from submitted form
        filename = request.form.get('filename')
        # Use getlist for year multi-select
        selected_years = request.form.getlist('year') 
        # Use getlist for type multi-select
        selected_types = request.form.getlist('type') 
        keywords = request.form.get('keywords')
        # Store list of years/types in search_terms for refilling form
        search_terms = {'filename': filename, 'year': selected_years, 'type': selected_types, 'keywords': keywords}
    else: # request.method == 'GET'
        # Get data from URL parameters (e.g., from tag cloud links)
        filename = request.args.get('filename')
        # GET requests typically won't have multiple years/types from links
        year_single = request.args.get('year') 
        file_type_single = request.args.get('type') 
        keywords = request.args.get('keywords')
        # Populate search_terms to refill the form fields if parameters are in URL
        selected_years = [year_single] if year_single else []
        selected_types = [file_type_single] if file_type_single else []
        search_terms = {'filename': filename, 'year': selected_years, 'type': selected_types, 'keywords': keywords}

    # Perform search if any search term is provided (from POST or GET)
    # Note: search_terms['year'] and ['type'] are now lists
    if any(st for key, st in search_terms.items() if st): # Check for non-empty values/lists
        results = search_database(filename=filename, years=selected_years, file_types=selected_types, keywords=keywords)
    else:
         # Optional: Add a flash message telling the user to enter search terms if method was POST
         # if request.method == 'POST': flash("Please enter search terms.")
         pass

    # Get distinct file types for the dropdown
    distinct_types = get_distinct_file_types()
    # Get distinct years for the dropdown
    distinct_years = get_distinct_years()
    # Always get top keywords for the tag cloud
    top_keywords = get_top_keywords(limit=50) # Get top 50 keywords
    print(f"DEBUG: Top Keywords Data (first 5): {top_keywords[:5]}") # Add this debug print

    # On GET or after POST, render the template with results and previous terms
    return render_template('index.html', results=results, 
                           search_terms=search_terms, 
                           top_keywords=top_keywords,
                           distinct_types=distinct_types,
                           distinct_years=distinct_years)

@app.route('/download/') # Note the trailing slash
@app.route('/download/<path:file_path>')
def download_file(file_path=None):
    """Serves a requested file for download after security checks."""
    if not file_path:
        abort(404) # No file path provided

    # --- Security Check --- 
    # 1. Normalize the path to prevent directory traversal ('../')
    # os.path.abspath ensures it starts from root, preventing relative paths outside the intended dir
    # We prepend / to file_path because the indexed paths are absolute
    safe_path = os.path.abspath(os.path.join("/", file_path)) # Treat incoming path as relative to root
    
    # 2. Ensure the requested path is within the allowed INDEXED_ROOT_DIR
    # os.path.commonpath requires Python 3.5+ 
    # For broader compatibility, we check if safe_path starts with the root dir
    if not safe_path.startswith(os.path.abspath(INDEXED_ROOT_DIR) + os.sep):
        print(f"Attempt to access file outside allowed directory: {safe_path}")
        abort(403) # Forbidden

    # 3. Check if the file actually exists
    if not os.path.isfile(safe_path):
        print(f"Requested file not found: {safe_path}")
        abort(404) # Not Found

    try:
        # Use send_file to handle MIME types and download prompts
        # as_attachment=True forces the browser download dialog
        return send_file(safe_path, as_attachment=True)
    except Exception as e:
        print(f"Error sending file '{safe_path}': {e}")
        abort(500) # Internal Server Error

@app.route('/download_backup/<filename>')
def download_backup(filename):
    """Serves a requested database backup file."""
    # Basic security: ensure filename doesn't contain path traversal
    if '..' in filename or filename.startswith('/'):
        abort(400) # Bad request

    backup_file_path = os.path.join(BACKUP_DIR, filename)

    # --- Security Check ---
    # Ensure the file is within the designated BACKUP_DIR
    if not os.path.abspath(backup_file_path).startswith(os.path.abspath(BACKUP_DIR)):
         print(f"Attempt to access backup file outside allowed directory: {backup_file_path}")
         abort(403) # Forbidden

    if not os.path.isfile(backup_file_path):
        abort(404) # Not Found

    try:
        return send_file(backup_file_path, as_attachment=True)
    except Exception as e:
        print(f"Error sending backup file '{backup_file_path}': {e}")
        abort(500)

@app.route('/download_code_backup/<filename>')
def download_code_backup(filename):
    """Serves a requested commit-specific code backup (.zip) file."""
    # Basic security: ensure filename doesn't contain path traversal
    if '..' in filename or filename.startswith('/') or not filename.endswith('.zip'):
        abort(400) # Bad request

    backup_file_path = os.path.join(BACKUP_DIR, filename)

    # --- Security Check ---
    # Ensure the file is within the designated BACKUP_DIR
    if not os.path.abspath(backup_file_path).startswith(os.path.abspath(BACKUP_DIR)):
         logger.warning(f"Attempt to access code backup file outside allowed directory: {backup_file_path}")
         abort(403) # Forbidden

    if not os.path.isfile(backup_file_path):
        logger.warning(f"Requested code backup file not found: {backup_file_path}")
        abort(404) # Not Found

    try:
        return send_file(backup_file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error sending code backup file '{backup_file_path}': {e}")
        abort(500)

@app.route('/history')
def history():
    """Displays git commit history and lists available backups."""
    # Get Git log
    history_log = []
    try:
        # Use a format that's easy to parse/display
        log_format = "%h -- %ad -- %s" # hash -- date -- subject
        date_format = "%Y-%m-%d %H:%M" # Short date format
        git_log_cmd = ["git", "log", "--pretty=format:" + log_format, "--date=format:" + date_format, "-n", "30"] # Show last 30 commits
        
        result = subprocess.run(git_log_cmd, capture_output=True, text=True, check=True)
        history_log = result.stdout.strip().split('\n')
    except FileNotFoundError:
        history_log = ["Error: 'git' command not found. Is Git installed and in PATH?"]
        logger.error("'git' command not found when trying to get commit history.")
    except subprocess.CalledProcessError as e:
        history_log = [f"Error running git log: {e.stderr}"]
        logger.error(f"Error running git log: {e.stderr}")
    except Exception as e:
        history_log = [f"An unexpected error occurred retrieving git log: {e}"]
        logger.error(f"An unexpected error occurred retrieving git log: {e}")

    # Get Backups
    manual_db_backups = []
    commit_db_backups = []
    commit_code_backups = []
    try:
        all_files = sorted(os.listdir(BACKUP_DIR), reverse=True) # Sort by name (descending)
        manual_db_backups = [f for f in all_files if f.startswith('file_index_') and f.endswith('.db')]
        commit_db_backups = [f for f in all_files if f.startswith('db_commit_') and f.endswith('.db')]
        commit_code_backups = [f for f in all_files if f.startswith('code_commit_') and f.endswith('.zip')]
    except FileNotFoundError:
        logger.warning(f"Backup directory '{BACKUP_DIR}' not found.")
    except Exception as e:
        logger.error(f"Error listing backup directory '{BACKUP_DIR}': {e}")

    return render_template('history.html', 
                           history_log=history_log, 
                           manual_db_backups=manual_db_backups,
                           commit_db_backups=commit_db_backups,
                           commit_code_backups=commit_code_backups)

@app.route('/browse/')
@app.route('/browse/<path:sub_path>')
def browse(sub_path=''):
    """Displays directories and files for browsing."""
    # --- Security and Path Handling ---
    base_dir = os.path.abspath(INDEXED_ROOT_DIR)
    # Prevent access above the base directory
    requested_path = os.path.abspath(os.path.join(base_dir, sub_path))
    
    if not requested_path.startswith(base_dir):
        print(f"Attempt to browse outside allowed directory: {requested_path}")
        abort(403) # Forbidden
        
    if not os.path.isdir(requested_path):
        abort(404) # Not a valid directory

    # --- List Directory Contents ---
    dirs = []
    files = []
    try:
        for item in os.listdir(requested_path):
            item_path = os.path.join(requested_path, item)
            # Generate relative path for links
            relative_item_path = os.path.relpath(item_path, base_dir)
            
            if os.path.isdir(item_path):
                dirs.append({'name': item, 'path': relative_item_path})
            elif os.path.isfile(item_path):
                # Get file metadata from DB if available
                # Note: item_path is absolute here, matching DB paths
                file_info = query_db("""SELECT filename, category_type, category_year, keywords 
                                         FROM files WHERE path = ?""", [item_path], one=True)
                files.append({
                    'name': item,
                    'path': item_path, # Keep absolute for download link
                    'info': file_info # This might be None if not indexed
                })
        # Sort directories and files alphabetically
        dirs.sort(key=lambda x: x['name'].lower())
        files.sort(key=lambda x: x['name'].lower())
        
    except PermissionError:
        abort(403)
    except Exception as e:
        print(f"Error browsing directory '{requested_path}': {e}")
        abort(500)

    # --- Breadcrumb Navigation ---
    path_parts = sub_path.split(os.sep)
    breadcrumbs = []
    current_crumb_path = ''
    breadcrumbs.append({'name': 'Archive Root', 'path': ''}) # Link to base browse page
    for i, part in enumerate(path_parts):
        if part:
            current_crumb_path = os.path.join(current_crumb_path, part)
            breadcrumbs.append({'name': part, 'path': current_crumb_path})

    # Don't show the last part as a link in breadcrumbs
    if len(breadcrumbs) > 1:
        breadcrumbs[-1]['is_last'] = True 

    return render_template('browse.html', 
                           current_path=sub_path or '/', 
                           breadcrumbs=breadcrumbs,
                           directories=dirs, 
                           files=files)

@app.route('/download_code')
def download_code():
    """Creates a zip archive of the source code and sends it."""
    # Define which files/dirs to include
    # Exclude backups, venv, db, logs etc. (already in .gitignore, but good practice here too)
    project_files = [
        'app.py',
        'indexer.py',
        'searcher.py', # Include the CLI searcher too
        'requirements.txt',
        'VERSION',
        '.gitignore',
        'templates/index.html',
        'templates/history.html'
    ]
    
    memory_file = io.BytesIO()
    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in project_files:
                if os.path.exists(f):
                    zf.write(f, arcname=f) # Add file with its path
                else:
                    print(f"Warning: File not found for zipping: {f}") # Log missing files
            
            # Add templates directory content (if not empty and exists)
            if os.path.isdir('templates'):
                 for root, _, files in os.walk('templates'):
                    for file in files:
                         file_path = os.path.join(root, file)
                         arcname = os.path.relpath(file_path, start='.') # Use relative path in zip
                         zf.write(file_path, arcname=arcname)
                         
        memory_file.seek(0)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"dol_data_archiver_code_{timestamp}.zip"
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
    except Exception as e:
        print(f"Error creating code zip file: {e}")
        abort(500)

@app.route('/download_package')
def download_package():
    """Creates a zip archive of the source code and current database."""
    # Define files to include (same as download_code plus database)
    project_files = [
        'app.py',
        'indexer.py',
        'searcher.py',
        'requirements.txt',
        'VERSION',
        '.gitignore',
        DATABASE # Add the database file name
    ]
    
    memory_file = io.BytesIO()
    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add individual files
            for f in project_files:
                if os.path.exists(f):
                    zf.write(f, arcname=f)
                else:
                    print(f"Warning: File not found for zipping: {f}")
            
            # Add templates directory
            if os.path.isdir('templates'):
                 for root, _, files in os.walk('templates'):
                    for file in files:
                         file_path = os.path.join(root, file)
                         arcname = os.path.relpath(file_path, start='.') 
                         zf.write(file_path, arcname=arcname)
                         
        memory_file.seek(0)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"dol_data_archiver_package_{timestamp}.zip"
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
    except Exception as e:
        print(f"Error creating package zip file: {e}")
        abort(500)

# Add logger setup if not already present
logging.basicConfig(level=logging.DEBUG) # Use DEBUG for development
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    print("Starting Flask web server...")
    print("Ensure the database '{}' exists (run indexer.py first).".format(DATABASE))
    print("Access the application at http://127.0.0.1:5000")
    # Use debug=True only for development, not production
    app.run(debug=True, host='0.0.0.0') # Host 0.0.0.0 makes it accessible on network 