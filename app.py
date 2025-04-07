import sqlite3
import os
import subprocess # For running git log
import zipfile
import io
import datetime # For timestamp in zip filename
import shutil # Import shutil for file copying
from flask import Flask, render_template, request, g, send_file, abort, flash, redirect, url_for, current_app # Add flash, redirect, url_for, current_app
from collections import Counter
import math # For tag cloud scaling
import logging
import re # For parsing git log
import glob # For globbing file patterns

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) # Needed for flash messages, etc.

# Set default config values (can be overridden by instance config or tests)
app.config.setdefault('DATABASE', 'file_index.db')
app.config.setdefault('INDEXED_ROOT_DIR', '/dol-data-archive2') # Ensure this default is correct
app.config.setdefault('BACKUP_DIR', 'backups') # Default backup dir

# --- App Initialization --- 
@app.before_request
def before_request():
    # Ensure backup directory exists before handling requests that might use it
    backup_dir = current_app.config.get('BACKUP_DIR', 'backups') # Use default if not set
    os.makedirs(backup_dir, exist_ok=True)
    # Make DATABASE and BACKUP_DIR easily accessible in templates if needed
    g.DATABASE = current_app.config['DATABASE']
    g.BACKUP_DIR = current_app.config['BACKUP_DIR']
    
def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    db = getattr(g, '_database', None)
    if db is None:
        if not os.path.exists(current_app.config['DATABASE']):
             # In a real app, handle this more gracefully, maybe redirect to an error page
             raise FileNotFoundError(f"Database file '{current_app.config['DATABASE']}' not found. Run indexer first.")
        db = g._database = sqlite3.connect(current_app.config['DATABASE'])
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
    db_path = current_app.config['DATABASE'] # Use config
    backup_dir = current_app.config['BACKUP_DIR'] # Use config
    
    if not os.path.exists(db_path):
        logger.error(f"Database file {db_path} not found, cannot create backup.")
        return None

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"file_index_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        shutil.copy2(db_path, backup_path) # copy2 preserves metadata
        logger.info(f"Database backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create database backup to {backup_dir}: {e}")
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
    if not safe_path.startswith(os.path.abspath(current_app.config['INDEXED_ROOT_DIR']) + os.sep):
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
    backup_dir = current_app.config['BACKUP_DIR'] # Use config
    # Basic security: ensure filename doesn't contain path traversal
    if '..' in filename or filename.startswith('/'):
        abort(400) # Bad request

    backup_file_path = os.path.join(backup_dir, filename)

    # --- Security Check ---
    # Ensure the file is within the designated BACKUP_DIR
    if not os.path.abspath(backup_file_path).startswith(os.path.abspath(backup_dir)):
         logger.warning(f"Attempt to access backup file outside allowed directory: {backup_file_path}")
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
    backup_dir = current_app.config['BACKUP_DIR'] # Use config
    # Basic security: ensure filename doesn't contain path traversal
    if '..' in filename or filename.startswith('/') or not filename.endswith('.zip'):
        abort(400) # Bad request

    backup_file_path = os.path.join(backup_dir, filename)

    # --- Security Check ---
    # Ensure the file is within the designated BACKUP_DIR
    if not os.path.abspath(backup_file_path).startswith(os.path.abspath(backup_dir)):
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

@app.route('/restore_backup/<filename>', methods=['POST'])
def restore_backup(filename):
    """Restores the database from a selected backup file."""
    backup_dir = current_app.config['BACKUP_DIR'] # Use config
    live_db_path = current_app.config['DATABASE'] # Use config
    
    # Security: Prevent path traversal and ensure it's a .db file
    if '..' in filename or filename.startswith('/') or not filename.endswith('.db'):
        logger.error(f"Attempt to restore invalid file: {filename}")
        flash("Invalid backup filename provided.", 'error')
        abort(400) # Bad request

    backup_file_path = os.path.join(backup_dir, filename)

    # --- Security & Existence Checks ---
    # Ensure the backup file is within the designated BACKUP_DIR
    if not os.path.abspath(backup_file_path).startswith(os.path.abspath(backup_dir)):
         logger.error(f"Attempt to restore file outside allowed directory: {backup_file_path}")
         flash("Invalid backup file location.", 'error')
         abort(403) # Forbidden

    if not os.path.isfile(backup_file_path):
        logger.error(f"Backup file not found for restore: {backup_file_path}")
        flash(f"Backup file '{filename}' not found.", 'error')
        abort(404) # Not Found
        
    # --- Perform Restore --- 
    try:
        # Important: Ensure any active DB connection is closed before overwriting?
        # Flask usually handles connections per request, so it *should* be okay,
        # but in a more complex app, explicit connection closing might be needed here.
        logger.warning(f"Attempting to restore database from: {backup_file_path} to {live_db_path}")
        shutil.copy2(backup_file_path, live_db_path) # copy2 preserves metadata
        logger.info(f"Database successfully restored from {filename}.")
        flash(f"Database successfully restored from '{filename}'.", 'success')
    except Exception as e:
        logger.error(f"Failed to restore database from '{filename}': {e}")
        flash(f"Failed to restore database: {e}", 'error')
        # Don't abort here, redirect back to history to show the error

    return redirect(url_for('history'))

def get_tag_details():
    """Gets details for each Git tag (name, commit hash, date, subject)."""
    tags = []
    try:
        # Format: tagname<SEP>commithash<SEP>commitdate(iso8601)<SEP>subject
        # Use a unique separator like <||> unlikely to be in subject
        sep = "<||>"
        # List tags, dereference to get commit info, sort by version descending
        cmd = [
            'git', 'tag', '-l', 'v*', '--sort=-v:refname', 
            f'--format=%(refname:short){sep}%(objectname:short){sep}%(committerdate:iso8601){sep}%(subject)'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(sep, 3)
            if len(parts) == 4:
                tag_name, commit_hash, date_str, subject = parts
                tags.append({
                    'name': tag_name,
                    'hash': commit_hash,
                    'date': date_str.split(' ')[0], # Just get YYYY-MM-DD
                    'subject': subject
                })
    except FileNotFoundError:
        logger.error("'git' command not found when trying to get tag details.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running git tag command: {e.stderr}")
    except Exception as e:
        logger.error(f"An unexpected error occurred retrieving tag details: {e}")
    return tags

@app.route('/download_commit_package/<commit_hash>')
def download_commit_package(commit_hash):
    """Creates a zip archive of the code and DB backup for a specific commit hash."""
    backup_dir = current_app.config['BACKUP_DIR']
    # Basic validation
    if not re.match(r'^[a-f0-9]+$', commit_hash):
        abort(400, "Invalid commit hash format.")
        
    # We expect filenames based on the post-commit hook (which uses short hash)
    # Use the first 7 chars from the input hash for consistency
    short_hash = commit_hash[:7]
    
    # Use glob to find matching files, prioritizing the short hash pattern
    db_backup_glob = os.path.join(backup_dir, f"db_commit_{short_hash}*.db")
    code_backup_glob = os.path.join(backup_dir, f"code_commit_{short_hash}*.zip")
    
    db_backup_files = glob.glob(db_backup_glob)
    code_backup_files = glob.glob(code_backup_glob)

    # Check if files exist
    if not db_backup_files:
        logger.warning(f"Commit DB backup not found matching pattern {db_backup_glob}")
        abort(404) # Not Found
    if not code_backup_files:
        logger.warning(f"Commit Code backup not found matching pattern {code_backup_glob}")
        abort(404) # Not Found

    # Use the first match found by glob
    db_backup_file = db_backup_files[0]
    code_backup_file = code_backup_files[0]
    logger.info(f"Found backup files for commit {short_hash}: DB={os.path.basename(db_backup_file)}, Code={os.path.basename(code_backup_file)}")

    # --- Create a temporary zip file ---
    output_filename = f"DenkraumNavigator_package_{commit_hash}.zip"
    memory_file = io.BytesIO()

    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add the DB backup
            zf.write(db_backup_file, arcname=os.path.basename(db_backup_file)) 
            
            # Add the code backup contents (extract and re-add to avoid nested zip)
            # Alternatively, just include both zips? Let's add the code zip directly for simplicity.
            zf.write(code_backup_file, arcname=os.path.basename(code_backup_file))
            
            # Optionally add other project files like notes, version, etc.
            if os.path.exists('PROJECT_NOTES.md'):
                zf.write('PROJECT_NOTES.md', arcname='PROJECT_NOTES.md')
            if os.path.exists('CHANGELOG.md'):
                 zf.write('CHANGELOG.md', arcname='CHANGELOG.md')
            if os.path.exists('VERSION'):
                 zf.write('VERSION', arcname='VERSION')
                 
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=output_filename
        )
    except Exception as e:
        logger.error(f"Error creating package zip for commit {commit_hash}: {e}")
        abort(500)

def get_commit_details(limit=50):
    """Gets details for the most recent commits, including associated tags and backup status."""
    commits = []
    backup_dir = current_app.config.get('BACKUP_DIR', 'backups')
    # Format: hash<|>date_iso<|>subject<|>tag_refs
    # %d gives ref names like (HEAD -> master, tag: v0.1.0)
    format_string = "%h<|>%cI<|>%s<|>%d"
    try:
        # Git log command to get details for the last 'limit' commits
        command = ["git", "log", f"--pretty=format:{format_string}", f"-n{limit}"]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        lines = result.stdout.strip().split('\n')

        for line in lines:
            if not line:
                continue
            parts = line.split('<|>', 3)
            if len(parts) == 4:
                commit_hash, commit_date, subject, refs = parts
                # Extract tags from refs
                # Refs look like: (HEAD -> master, tag: v0.1.0, origin/master)
                tags = re.findall(r'tag: ([^,\)]+)', refs)
                tag_string = ", ".join(tags) if tags else ""

                # Check for backup file existence
                db_backup_pattern = os.path.join(backup_dir, f"db_commit_{commit_hash}*.db")
                code_backup_pattern = os.path.join(backup_dir, f"code_commit_{commit_hash}*.zip")
                db_exists = bool(glob.glob(db_backup_pattern))
                code_exists = bool(glob.glob(code_backup_pattern))
                backups_exist = db_exists and code_exists

                commits.append({
                    'hash': commit_hash,
                    'date': commit_date,
                    'subject': subject,
                    'tags': tag_string,
                    'backups_exist': backups_exist
                })
            else:
                 logger.warning(f"Could not parse git log line: {line}")

    except FileNotFoundError:
        logger.error("Git command not found. Is Git installed and in PATH?")
        return []
    except subprocess.CalledProcessError as e:
        logger.error(f"Git log command failed: {e}")
        logger.error(f"Git stderr: {e.stderr}")
        return []
    except Exception as e:
        logger.error(f"Error processing git log for commits: {e}")
        return []
    return commits

@app.route('/history')
def history():
    """Displays version history, tags, backups, and commit log."""
    backup_dir = current_app.config['BACKUP_DIR'] # Use config
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)

    # Get Tag Details
    tag_details = get_tag_details()

    # Get Commit Details (New Function)
    commit_details = get_commit_details(limit=50) # Get last 50 commits

    # Get lists of backup files (Manual only now)
    manual_db_backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('file_index_') and f.endswith('.db')], reverse=True)
    # Remove the old commit backup file lists
    # commit_db_backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('db_commit_') and f.endswith('.db')], reverse=True)
    # commit_code_backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('code_commit_') and f.endswith('.zip')], reverse=True)

    return render_template('history.html', 
                           tag_details=tag_details,
                           commit_details=commit_details, # Pass commit details
                           manual_db_backups=manual_db_backups)
                           # Remove old backup lists
                           # commit_db_backups=commit_db_backups,
                           # commit_code_backups=commit_code_backups)

@app.route('/browse/')
@app.route('/browse/<path:sub_path>')
def browse(sub_path=''):
    """Displays directories and files for browsing."""
    # --- Security and Path Handling ---
    base_dir = os.path.abspath(current_app.config['INDEXED_ROOT_DIR'])
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
        current_app.config['DATABASE'] # Add the database file name
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
    # Access config via the app object here, not current_app
    print("Ensure the database '{}' exists (run indexer.py first).".format(app.config['DATABASE']))
    print("Access the application at http://127.0.0.1:5000")
    # Use debug=True only for development, not production
    app.run(debug=True, host='0.0.0.0') # Host 0.0.0.0 makes it accessible on network 