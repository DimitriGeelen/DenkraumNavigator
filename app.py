import sqlite3
import os
import subprocess # For running git log
import zipfile
import io
import datetime # For timestamp in zip filename
from flask import Flask, render_template, request, g, send_file, abort
from collections import Counter
import math # For tag cloud scaling

DATABASE = 'file_index.db'
# IMPORTANT: Define the root directory that contains the indexed files for security
# This should be the directory you passed to indexer.py (e.g., /dol-data-archive2)
INDEXED_ROOT_DIR = "/dol-data-archive2"
BACKUP_DIR = "backups"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) # Needed for flash messages, etc.

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
        max_count = top_keywords[0][1]
        min_count = top_keywords[-1][1]
        # Apply log scaling to prevent huge differences, avoid log(0 or 1)
        scaled_keywords = [
            (kw, count, 1 + math.log(max(1, count))) 
            for kw, count in top_keywords
        ]
        # Normalize the log scale for font size (e.g., 1 to 5)
        max_log_count = max(s[2] for s in scaled_keywords)
        min_log_count = min(s[2] for s in scaled_keywords)
        range_log = max_log_count - min_log_count
        
        final_keywords = []
        for kw, count, log_count in scaled_keywords:
            if range_log > 0:
                # Scale font size from, say, 1 (min) to 4 (max) relative units
                font_scale = 1 + 3 * (log_count - min_log_count) / range_log 
            else:
                font_scale = 2 # Default size if all counts are the same
            final_keywords.append({'text': kw, 'weight': count, 'font_scale': font_scale})
        # print(f"DEBUG [get_top_keywords]: Final scaled keywords (first 5): {final_keywords[:5]}") # Debug
        return final_keywords
    else:
        print("DEBUG [get_top_keywords]: No top keywords found after counting.") # Debug
        return []

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
    if '..' in filename or '/' in filename:
        abort(400) # Bad request
        
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    if not os.path.isfile(backup_path):
        abort(404) # Not Found
        
    try:
        return send_file(backup_path, as_attachment=True)
    except Exception as e:
        print(f"Error sending backup file '{backup_path}': {e}")
        abort(500)

@app.route('/history')
def history():
    """Displays the git commit history and available backups."""
    # Get Git history
    try:
        # Run git log, get limited output, decode to string
        # Use a format that's easy to parse/display
        log_format = "%h -- %ad -- %s" # hash -- date -- subject
        date_format = "%Y-%m-%d %H:%M" # Short date format
        git_log_cmd = ["git", "log", "--pretty=format:" + log_format, "--date=format:" + date_format, "-n", "30"] # Show last 30 commits
        
        result = subprocess.run(git_log_cmd, capture_output=True, text=True, check=True)
        history_log = result.stdout.strip().split('\n')
    except FileNotFoundError:
        history_log = ["Error: 'git' command not found. Is Git installed and in PATH?"]
    except subprocess.CalledProcessError as e:
        history_log = [f"Error running git log: {e.stderr}"]
    except Exception as e:
        history_log = [f"An unexpected error occurred: {e}"]
    
    # Get available backups
    backup_files = []
    try:
        if os.path.isdir(BACKUP_DIR):
            # List files, sort by modification time (newest first) might be better?
            # Or just alphabetical which groups by date in filename
            backup_files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')], reverse=True)
    except Exception as e:
        print(f"Error listing backup directory '{BACKUP_DIR}': {e}")
        # Optionally add an error message to display on the page
        
    return render_template('history.html', history_log=history_log, backup_files=backup_files)

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

if __name__ == '__main__':
    print("Starting Flask web server...")
    print("Ensure the database '{}' exists (run indexer.py first).".format(DATABASE))
    print("Access the application at http://127.0.0.1:5000")
    # Use debug=True only for development, not production
    app.run(debug=True, host='0.0.0.0') # Host 0.0.0.0 makes it accessible on network 