# print("DEBUG: TOP OF app.py EXECUTING", flush=True)
import sqlite3
import os
import subprocess # For running git log
import zipfile
import io
import datetime # For timestamp in zip filename
import shutil # Import shutil for file copying
from flask import Flask, render_template, request, g, send_file, abort, flash, redirect, url_for, current_app, Response # Add flash, redirect, url_for, current_app
from collections import Counter
import math # For tag cloud scaling
import logging
import re # For parsing git log
import glob # For globbing file patterns
import markdown # Import the markdown library
from logging.handlers import RotatingFileHandler # Import handler
import ast # <-- Add import for Abstract Syntax Trees

# --- Add Pillow import ---
from PIL import Image, UnidentifiedImageError

# --- Logger Setup ---
# Moved from bottom to ensure logger is available globally at startup
# logging.basicConfig(level=logging.INFO) # Use INFO to reduce verbosity
logger = logging.getLogger(__name__) # Reinstate global logger for initial parsing

# --- Flask App Setup ---
app = Flask(__name__)

# --- Configuration Loading ---
# Load configuration from environment variables with defaults

# Get the archive root directory from environment or use default
# Ensures path is absolute
default_archive_dir = '/dol-data-archive2'
archive_dir_env = os.environ.get('DENKRAUM_ARCHIVE_DIR')
if archive_dir_env:
    app.config['INDEXED_ROOT_DIR'] = os.path.abspath(archive_dir_env)
    print(f"[INFO] Loaded INDEXED_ROOT_DIR from environment: {app.config['INDEXED_ROOT_DIR']}")
else:
    app.config['INDEXED_ROOT_DIR'] = os.path.abspath(default_archive_dir)
    print(f"[INFO] Using default INDEXED_ROOT_DIR: {app.config['INDEXED_ROOT_DIR']}")

# Default Database Path (can be overridden by tests or future config)
app.config['DATABASE'] = os.environ.get('DENKRAUM_DB_PATH', 'file_index.db')
# --- End Configuration Loading ---

# Explicitly configure logging
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
log_handler = RotatingFileHandler('flask_explicit.log', maxBytes=1000000, backupCount=3)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.DEBUG) # Set desired level here (Changed to DEBUG)
app.logger.addHandler(log_handler)
app.logger.setLevel(logging.DEBUG) # Also set app logger level (Changed to DEBUG)

# Remove default Flask handler if it exists (optional, but cleaner)
if len(app.logger.handlers) > 1:
    app.logger.removeHandler(app.logger.handlers[0])

app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24)) # Use env var or random

# Set other default config values (can be overridden by instance config or tests)
app.config.setdefault('BACKUP_DIR', 'backups')
app.config.setdefault('THUMBNAIL_CACHE_DIR', 'thumbnail_cache')
app.config.setdefault('THUMBNAIL_SIZE', (100, 100)) # Width, Height

# --- Database Handling ---
DATABASE_PATH = app.config['DATABASE'] # Store for convenience

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
    """Fetches keywords row by row and returns the most frequent ones."""
    logger.debug("[get_top_keywords] Fetching keywords row by row...")
    keyword_counts = Counter()
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT keywords FROM files WHERE keywords IS NOT NULL AND keywords != ''")
        # Fetch and process row by row to reduce memory load
        row_count = 0
        while True:
            row = cur.fetchone() # Fetch one row
            if row is None:
                break # No more rows
            row_count += 1
            if row['keywords']:
                keywords = row['keywords'].split(',')
                keyword_counts.update(kw.strip() for kw in keywords if kw.strip())
            # Optional: Add logging every N rows to see progress
            # if row_count % 1000 == 0:
            #     logger.debug(f"[get_top_keywords] Processed {row_count} rows...")

        logger.debug(f"[get_top_keywords] Finished processing {row_count} rows.")

    except sqlite3.Error as e:
        logger.error(f"[get_top_keywords] Database error: {e}")
        return [] # Return empty on error
    finally:
        cur.close()
        # Don't close the connection here, let teardown handle it

    top_keywords = keyword_counts.most_common(limit)
    logger.debug(f"[get_top_keywords] Top {limit} raw keyword counts (first 5): {top_keywords[:5]}")

    # Add scaling factor for font size (optional, adjust as needed)
    if top_keywords:
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
        # Use getlist for year/type multi-select AND filter out empty strings
        selected_years = [y for y in request.form.getlist('year') if y] 
        selected_types = [t for t in request.form.getlist('type') if t] 
        keywords = request.form.get('keywords')
        # Store list of years/types in search_terms for refilling form
        search_terms = {'filename': filename, 'year': selected_years, 'type': selected_types, 'keywords': keywords}
    else: # request.method == 'GET'
        # Get data from URL parameters (e.g., from tag cloud links)
        filename = request.args.get('filename')
        year_single = request.args.get('year') 
        file_type_single = request.args.get('type') 
        keywords = request.args.get('keywords')
        # Filter out potential empty strings here too for consistency
        selected_years = [year_single] if year_single else []
        selected_types = [file_type_single] if file_type_single else []
        search_terms = {'filename': filename, 'year': selected_years, 'type': selected_types, 'keywords': keywords}

    # Perform search if any search term is provided (from POST or GET)
    # Note: search_terms['year'] and ['type'] are now lists
    if any(st for key, st in search_terms.items() if st): # Check for non-empty values/lists
        results = search_database(filename=filename, years=selected_years, file_types=selected_types, keywords=keywords)
    else:
         pass

    # Get distinct file types for the dropdown
    distinct_types = get_distinct_file_types()
    # Get distinct years for the dropdown
    distinct_years = get_distinct_years()
    # Get top keywords for the tag cloud (this might be slow for large datasets)
    top_keywords = get_top_keywords()
    # print(f"DEBUG: Top Keywords Data (first 5): {top_keywords[:5]}") # Add this debug print

    # *** ADD LOGGING HERE ***
    logger.info(f"[Route: /] Value of main_menu being passed to template: {g.main_menu}")

    # Define page sections for floating nav
    page_nav_items = []
    page_nav_items.append({'text': 'Filters', 'href': '#filters'})
    if top_keywords:
        page_nav_items.append({'text': 'Keywords', 'href': '#keywords'})
    # Always add results section, even if empty initially
    page_nav_items.append({'text': 'Results', 'href': '#results'})

    # On GET or after POST, render the template with results and previous terms
    return render_template('index.html', results=results,
                           search_terms=search_terms,
                           top_keywords=top_keywords,
                           distinct_types=distinct_types,
                           distinct_years=distinct_years,
                           page_nav_items=page_nav_items) # Pass nav items

@app.route('/download/') # Note the trailing slash
@app.route('/download/<path:file_path>')
def download_file(file_path=None):
    """Serves a requested file for download after security checks."""
    if not file_path:
        abort(404) # No file path provided

    # --- Security Check (Revised based on serve_thumbnail logic) ---
    # 1. Get the absolute path of the configured root directory
    indexed_root_abs = os.path.abspath(current_app.config['INDEXED_ROOT_DIR'])
    
    # 2. Join the requested file_path with the root directory and then normalize
    requested_path = os.path.join(indexed_root_abs, file_path)
    safe_path = os.path.abspath(requested_path)
    
    # 3. Ensure the final normalized path is still within the root directory
    if not safe_path.startswith(indexed_root_abs + os.sep):
        logger.warning(f"Attempt to access file outside allowed directory: {safe_path} (resolved from {file_path}, root: {indexed_root_abs})")
        abort(403) # Forbidden

    # 4. Check if the file actually exists
    if not os.path.isfile(safe_path):
        logger.warning(f"Requested file not found for download: {safe_path}")
        abort(404) # Not Found

    try:
        # Use send_file to handle MIME types and download prompts
        # as_attachment=True forces the browser download dialog
        logger.info(f"Serving file for download: {safe_path}") # Log success
        return send_file(safe_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error sending file '{safe_path}': {e}")
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
    """Fetches details for version tags (vX.Y.Z)."""
    logger.info("Fetching version tag details.")
    # Format: tagname<|>commit_hash<|>date_iso<|>subject
    # Use %(refname:short) for tag name
    format_string = "%(refname:short)¦%(objectname:short)¦%(creatordate:iso8601)¦%(contents:subject)"
    cmd = ['git', 'tag', '-l', 'v*', f'--format={format_string}', '--sort=-creatordate']
    logger.debug(f"Running git command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
        output = result.stdout.strip()
        logger.debug(f"Raw git tag output: {output}")
    except FileNotFoundError:
        logger.error("Git command not found. Is Git installed and in PATH?")
        return []
    except subprocess.CalledProcessError as e:
        logger.error(f"Git tag command failed: {e}")
        logger.error(f"Git error output: {e.stderr}")
        return []
    except Exception as e:
         logger.error(f"An unexpected error occurred running git tag: {e}")
         return []

    tags = []
    if not output:
        logger.warning("Git tag output was empty.")
        return []

    # --- Ensure splitting by lines --- 
    lines = output.strip().splitlines() # Use splitlines() for robust splitting
    # --------------------------------
    logger.debug(f"Processing {len(lines)} lines from git tag output.") # Add log

    for i, line in enumerate(lines):
        parts = line.strip().split('¦', 3)
        if len(parts) == 4:
            tag_name, commit_hash, commit_date, subject = parts
            
            # --- Add Version Parsing and Changelog Fetch --- 
            version_tag_parsed = None
            release_notes_html = None
            version_match = re.match(r'^v?(\d+\.\d+\.\d+)$', tag_name)
            if version_match:
                version_tag_parsed = version_match.group(1) # Extract X.Y.Z
                logger.debug(f"[get_tag_details] Found version {version_tag_parsed} in tag '{tag_name}'. Fetching notes.")
                release_notes_html = get_changelog_notes(version_tag_parsed)
            # ---------------------------------------------

            tags.append({
                'name': tag_name,
                'hash': commit_hash,
                'date': commit_date.split('T')[0], # Just date part
                'subject': subject,
                'release_notes': release_notes_html # Add the fetched notes
            })
        else:
            logger.warning(f"Could not parse git tag line {i+1}: '{line}'. Expected 4 parts separated by '¦', got {len(parts)}.")

    logger.info(f"Finished processing tag details. Found {len(tags)} tags.")
    return tags

@app.route('/download_commit_package/<commit_hash>')
def download_commit_package(commit_hash):
    """Creates and sends a zip package containing code and DB backup for a specific commit."""
    backup_dir = 'backups'
    db_backup_glob = os.path.join(backup_dir, f'commit_{commit_hash}*.db')
    code_backup_glob = os.path.join(backup_dir, f'commit_{commit_hash}*.zip')
    logger.debug(f"Attempting to find backups for commit {commit_hash} in {backup_dir}")
    logger.debug(f"Using DB glob pattern: {db_backup_glob}")
    logger.debug(f"Using Code glob pattern: {code_backup_glob}")

    db_backup_files = glob.glob(db_backup_glob)
    code_backup_files = glob.glob(code_backup_glob)
    logger.debug(f"Glob result for DB pattern {db_backup_glob}: {db_backup_files}")
    logger.debug(f"Glob result for Code pattern {code_backup_glob}: {code_backup_files}")

    if not db_backup_files or not code_backup_files:
        logger.warning(f"Commit DB backup not found matching pattern {db_backup_glob}")
        logger.warning(f"Commit Code backup not found matching pattern {code_backup_glob}")
        abort(404, description="Required backup files not found for this commit.")

    # Use the first match found by glob
    db_backup_file = db_backup_files[0]
    code_backup_file = code_backup_files[0]
    logger.info(f"Found backup files for commit {commit_hash}: DB={os.path.basename(db_backup_file)}, Code={os.path.basename(code_backup_file)}")

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

def get_changelog_notes(version):
    """Reads CHANGELOG.md, finds notes for a version, and returns as HTML."""
    logger.debug(f"[get_changelog_notes] Attempting to get notes for version: '{version}'") # Log exact input
    filepath = 'CHANGELOG.md'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            changelog_content = f.read()
            logger.debug(f"[get_changelog_notes] Read {len(changelog_content)} chars from {filepath}. Starts with: {changelog_content[:100]}...") # Log snippet

        # Regex to find the version section and capture content until the next heading or EOF
        # Made more robust to whitespace variations
        # pattern_str = rf"^## \\[v?{re.escape(str(version))}\\].*?\\n(.*?)(?=\\n## |\\Z)" # Old pattern
        pattern_str = rf"^##.*?\[v?{re.escape(str(version))}\].*?\n\s*(.*?)(?=\n\s*## |\Z)" # New pattern: Added .*?, \s* after \n, and \s* in lookahead
        logger.debug(f"[get_changelog_notes] Using regex pattern: {pattern_str}")
        pattern = re.compile(pattern_str, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        match = pattern.search(changelog_content)

        if match:
            notes_markdown = match.group(1).strip()
            logger.debug(f"[get_changelog_notes] Regex matched! Extracted markdown (first 100 chars): {notes_markdown[:100]}...")
            if notes_markdown:
                html_notes = markdown.markdown(notes_markdown)
                logger.debug(f"[get_changelog_notes] Successfully rendered notes for {version}.")
                return f'<div class=\"changelog-notes\">{html_notes}</div>'
            else:
                logger.warning(f"[get_changelog_notes] Found section for {version} but no notes content after stripping.")
                return None
        else:
            logger.warning(f"[get_changelog_notes] Regex did NOT match for version: {version}")
            return None
    except FileNotFoundError:
        logger.error(f"[get_changelog_notes] {filepath} not found.")
        return None
    except Exception as e:
        logger.error(f"[get_changelog_notes] Error processing {filepath} for version {version}: {e}")
        return None

def get_commit_details(limit=50):
    """Fetches detailed commit history including tags and checks for backups."""
    logger.info(f"Fetching commit details (limit: {limit}).")
    # Use short hash %h for backup matching, full hash %H for uniqueness if needed elsewhere
    # Use '|' as separator, include decorations (%d) for tags/branches
    # Format: short_hash¦full_hash¦date¦subject¦author¦decorations
    format_string = f"--pretty=format:%h¦%H¦%ad¦%s¦%an¦%d"

    date_format = "--date=format:%Y-%m-%d %H:%M:%S"
    cmd = ['git', 'log', f'--max-count={limit}', date_format, format_string]
    logger.debug(f"Running git command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
        output = result.stdout.strip()
        logger.debug(f"Raw git log output (first 200 chars): {output[:200]}")
    except FileNotFoundError:
        logger.error("Git command not found. Is Git installed and in PATH?")
        return []
    except subprocess.CalledProcessError as e:
        logger.error(f"Git log command failed: {e}")
        logger.error(f"Git error output: {e.stderr}")
        return []
    except Exception as e:
         logger.error(f"An unexpected error occurred running git log: {e}")
         return []

    commits = []
    if not output:
        logger.warning("Git log output was empty.")
        return []

    backup_dir = current_app.config.get('BACKUP_DIR', 'backups')

    lines = output.split('\n')
    logger.debug(f"Processing {len(lines)} lines from git log.")

    for i, line in enumerate(lines):
        parts = line.strip().split('¦', 5) # Split by '¦' up to 5 times now
        if len(parts) == 6:
            short_hash, full_hash, commit_date, subject, author, decorations = parts
            tags = []
            version_tag = None
            # Parse decorations for tags
            if decorations:
                # Remove parentheses if present
                clean_decorations = decorations.strip().strip('()')
                decoration_parts = [d.strip() for d in clean_decorations.split(',')]
                for part in decoration_parts:
                    if part.startswith('tag: '):
                        tag_name = part.replace('tag: ', '').strip()
                        tags.append(tag_name)
                        # Check if it's a version tag (e.g., v1.2.3 or 1.2.3)
                        if re.match(r'^v?(\d+\.\d+\.\d+)$', tag_name):
                           if version_tag is None: # Only take the first version tag found
                               version_match = re.match(r'^v?(\d+\.\d+\.\d+)$', tag_name)
                               version_tag = version_match.group(1) # Extract X.Y.Z part
                               logger.debug(f"Found version tag {tag_name} (parsed as {version_tag}) for commit {short_hash}")

            # --- Use short_hash for backup check ---
            backup_dir = current_app.config.get('BACKUP_DIR', 'backups')
            # Use short_hash here
            db_backup_pattern = os.path.join(backup_dir, f"commit_{short_hash}.db")
            zip_backup_pattern = os.path.join(backup_dir, f"commit_{short_hash}.zip")
            logger.debug(f"[get_commit_details] Checking backups for {short_hash} ({full_hash}) in '{backup_dir}'") # Log both
            logger.debug(f"[get_commit_details]  DB pattern: '{db_backup_pattern}'")
            logger.debug(f"[get_commit_details]  ZIP pattern: '{zip_backup_pattern}'")

            db_glob_result = glob.glob(db_backup_pattern)
            zip_glob_result = glob.glob(zip_backup_pattern)
            logger.debug(f"[get_commit_details]  DB glob result: {db_glob_result}")
            logger.debug(f"[get_commit_details]  ZIP glob result: {zip_glob_result}")

            db_backup_exists = bool(db_glob_result)
            zip_backup_exists = bool(zip_glob_result)
            logger.debug(f"[get_commit_details]  => DB exists: {db_backup_exists}, ZIP exists: {zip_backup_exists}")

            # Fetch changelog notes if it's a version commit
            release_notes_html = None
            if version_tag:
                # --- Add Log ---
                logger.debug(f"[get_commit_details] Commit {short_hash} has version tag '{version_tag}'. Calling get_changelog_notes.")
                # -------------
                release_notes_html = get_changelog_notes(version_tag)

            commits.append({
                'hash': short_hash, # Use short hash for display/links now
                'full_hash': full_hash, # Keep full hash if needed
                'date': commit_date,
                'subject': subject,
                'author': author,
                'tags': tags,
                'version': version_tag,
                'has_db_backup': db_backup_exists,
                'has_zip_backup': zip_backup_exists,
                'release_notes': release_notes_html
            })
        else:
            logger.warning(f"Could not parse git log line {i+1}: '{line}'. Expected 6 parts separated by '¦', got {len(parts)}.")


    logger.info(f"Finished processing commit details. Found {len(commits)} commits.")
    # logger.debug(f"Example commit data (first one): {commits[0] if commits else 'None'}")
    return commits

@app.route('/history')
def history():
    """Displays the commit history, version tags, and backups."""
    logger.info("Accessing /history route.")

    # Fetch commit details (already includes release notes where applicable)
    commits_data = get_commit_details(limit=100)
    if commits_data is None:
        logger.error("Failed to get commit details for /history.")
        flash('Error retrieving commit history.', 'error')
        commits_data = []

    # Fetch tag details (restore this)
    tag_details = get_tag_details()
    if tag_details is None:
        logger.error("Failed to get tag details for /history.")
        flash('Error retrieving version tag history.', 'error')
        tag_details = []

    # Fetch manual backup list (restore this)
    backup_dir = current_app.config.get('BACKUP_DIR', 'backups')
    manual_db_backups = []
    try:
        if os.path.exists(backup_dir):
             # Correctly indented list comprehension
             manual_db_backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('file_index_') and f.endswith('.db')], reverse=True)
             logger.debug(f"Found manual backups: {manual_db_backups}")
        else:
            logger.warning(f"Manual backup directory not found: {backup_dir}")
    except Exception as e:
        logger.error(f"Error listing manual backups in {backup_dir}: {e}")
        flash('Error retrieving manual backups.', 'error')
        manual_db_backups = [] # Ensure it's defined even on error

    # Fetch and render COMMIT_VERSIONING_CHANGELOG.md content
    workflow_notes_html = ""
    try:
        with open('COMMIT_VERSIONING_CHANGELOG.md', 'r', encoding='utf-8') as f:
            md_content = f.read()
        workflow_notes_html = markdown.markdown(md_content)
        logger.debug("Successfully read and rendered COMMIT_VERSIONING_CHANGELOG.md")
    except FileNotFoundError:
        logger.warning("COMMIT_VERSIONING_CHANGELOG.md not found.")
        workflow_notes_html = "<p><em>COMMIT_VERSIONING_CHANGELOG.md not found.</em></p>"
    except Exception as e:
        logger.error(f"Error reading or rendering COMMIT_VERSIONING_CHANGELOG.md: {e}")
        workflow_notes_html = f"<p><em>Error loading workflow notes: {e}</em></p>"

    # Pass all necessary data to the template
    return render_template('history.html',
                           commits=commits_data,
                           tag_details=tag_details,
                           manual_db_backups=manual_db_backups,
                           workflow_notes_html=workflow_notes_html) # Add workflow notes

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

    # Define page sections for floating nav
    page_nav_items = []
    if dirs:
        page_nav_items.append({'text': 'Directories', 'href': '#directories'})
    if files:
        page_nav_items.append({'text': 'Files', 'href': '#files'})

    return render_template('browse.html', 
                           current_path=sub_path or '/', 
                           breadcrumbs=breadcrumbs,
                           directories=dirs, 
                           files=files,
                           page_nav_items=page_nav_items) # Pass nav items

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

# --- Project Goals Page ---

GOALS_FILE = 'PROJECT_GOALS.md'

@app.route('/goals')
def display_project_goals():
    """Displays the project goals in an editable textarea."""
    try:
        with open(GOALS_FILE, 'r', encoding='utf-8') as f:
            goals_content = f.read()
    except FileNotFoundError:
        goals_content = f"# {GOALS_FILE} not found.\\n\\nPlease create the file."
        logger.error(f"{GOALS_FILE} not found.")
    except Exception as e:
        goals_content = f"# Error reading {GOALS_FILE}\\n\\n{str(e)}"
        logger.error(f"Error reading {GOALS_FILE}: {e}")

    return render_template('goals.html', goals_content=goals_content)

@app.route('/update_goals', methods=['POST'])
def update_goals():
    """Receives POST request to update the project goals file."""
    new_content = request.form.get('goals_content')
    if new_content is None:
        flash('Error: No content received.', 'error')
        return redirect(url_for('display_project_goals'))

    try:
        # Basic sanitization: replace null bytes
        safe_content = new_content.replace('\x00', '')
        with open(GOALS_FILE, 'w', encoding='utf-8') as f:
             f.write(safe_content)
        flash(f'{GOALS_FILE} updated successfully.', 'success')
        logger.info(f"Updated {GOALS_FILE} via web interface.")
    except Exception as e:
        flash(f'Error updating {GOALS_FILE}: {e}', 'error')
        logger.error(f"Error writing {GOALS_FILE}: {e}")

    return redirect(url_for('display_project_goals'))

# --- End Project Goals Page ---

# --- Learnings Page ---

LEARNINGS_FILE = 'LEARNINGS.md'

@app.route('/learnings')
def display_learnings():
    """Displays the project learnings in an editable textarea."""
    try:
        with open(LEARNINGS_FILE, 'r', encoding='utf-8') as f:
            learnings_content = f.read()
    except FileNotFoundError:
        learnings_content = f"# {LEARNINGS_FILE} not found.\\n\\nPlease create the file."
        logger.error(f"{LEARNINGS_FILE} not found.")
    except Exception as e:
        learnings_content = f"# Error reading {LEARNINGS_FILE}\\n\\n{str(e)}"
        logger.error(f"Error reading {LEARNINGS_FILE}: {e}")

    return render_template('learnings.html', learnings_content=learnings_content)

@app.route('/update_learnings', methods=['POST'])
def update_learnings():
    """Receives POST request to update the project learnings file."""
    new_content = request.form.get('learnings_content')
    if new_content is None:
        flash('Error: No content received.', 'error')
        return redirect(url_for('display_learnings'))

    try:
        # Basic sanitization: replace null bytes
        safe_content = new_content.replace('\x00', '')
        with open(LEARNINGS_FILE, 'w', encoding='utf-8') as f:
             f.write(safe_content)
        flash(f'{LEARNINGS_FILE} updated successfully.', 'success')
        logger.info(f"Updated {LEARNINGS_FILE} via web interface.")
    except Exception as e:
        flash(f'Error updating {LEARNINGS_FILE}: {e}', 'error')
        logger.error(f"Error writing {LEARNINGS_FILE}: {e}")

    return redirect(url_for('display_learnings'))

# --- End Learnings Page ---

# --- Route to Download Change Notes ---
@app.route('/download_change_notes/<commit_hash>')
def download_change_notes(commit_hash):
    """Returns the commit message for a given hash as a text file download."""
    # Basic validation for commit hash (simple check for hex characters and length)
    if not all(c in '0123456789abcdef' for c in commit_hash) or not (7 <= len(commit_hash) <= 40):
        logger.warning(f"Invalid commit hash requested for download: {commit_hash}")
        abort(400, description="Invalid commit hash format.")

    try:
        # Use git log to get the raw commit body (%B)
        # -n 1: Limit to one commit
        result = subprocess.run(
            ['git', 'log', '-n', '1', '--pretty=format:%B', commit_hash],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8' # Ensure consistent encoding
        )
        commit_message = result.stdout

        # Create a response object for download
        response = Response(
            commit_message,
            mimetype='text/plain',
            headers={ "Content-Disposition": f"attachment; filename=change_notes_{commit_hash[:10]}.txt" }
        )
        logger.info(f"Served change notes for commit: {commit_hash}")
        return response

    except subprocess.CalledProcessError as e:
        # Handle case where commit hash doesn't exist or git command fails
        logger.error(f"Git command failed for commit {commit_hash}: {e}")
        logger.error(f"Git stderr: {e.stderr}")
        abort(404, description=f"Commit '{commit_hash}' not found or git error.")
    except FileNotFoundError:
        logger.error("Git command not found. Is Git installed and in PATH?")
        abort(500, description="Git command not found on server.")
    except Exception as e:
        logger.error(f"Error generating change notes for commit {commit_hash}: {e}")
        abort(500, description="Server error generating change notes.")
# --- End Change Notes Route ---

# --- Multi-MD File Editor Page ---

def sanitize_for_id(filename):
    """Sanitizes a filename to be used as an HTML ID."""
    # Remove .md extension
    base = os.path.splitext(filename)[0]
    # Replace non-alphanumeric characters (except hyphen) with hyphen
    sanitized = re.sub(r'[^a-zA-Z0-9-]', '-', base)
    # Remove leading/trailing hyphens and ensure it's not empty
    sanitized = sanitized.strip('-')
    return sanitized if sanitized else 'md-file' # Fallback ID

@app.route('/md_files')
def display_md_files():
    """Displays all root .md files for editing."""
    md_files_data = []
    page_nav_items = [] # Initialize list for floating nav
    try:
        md_filenames = sorted(glob.glob('*.md')) 
        
        for filename in md_filenames:
            file_id = sanitize_for_id(filename) # Generate ID for the section
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                md_files_data.append({
                    'filename': filename, 
                    'content': content,
                    'id': file_id # Add ID to data passed to template
                })
                # Add item for the floating navigation menu
                page_nav_items.append({
                    'text': filename,
                    'href': f'#{file_id}' # Link to the section ID
                })
            except Exception as e:
                logger.error(f"Error reading {filename}: {e}")
                md_files_data.append({
                    'filename': filename, 
                    'content': f"# Error reading file: {e}", 
                    'error': True,
                    'id': file_id # Still add ID even on error
                })
                
    except Exception as e:
        logger.error(f"Error finding .md files: {e}")
        flash(f"Error finding .md files: {e}", "error")
        # Optionally return an error template or redirect

    return render_template('md_files.html', 
                           md_files=md_files_data, 
                           page_nav_items=page_nav_items) # Pass nav items to template

@app.route('/update_md_file', methods=['POST'])
def update_md_file():
    """Receives POST request to update a specific .md file."""
    filename_to_update = request.form.get('filename')
    new_content = request.form.get('md_content')

    if not filename_to_update or new_content is None:
        flash('Error: Missing filename or content.', 'error')
        return redirect(url_for('display_md_files'))

    try:
        # Security Check: Ensure the filename is a valid .md file in the root
        valid_md_files = glob.glob('*.md')
        if filename_to_update not in valid_md_files:
            flash(f'Error: Invalid or disallowed filename: {filename_to_update}', 'error')
            logger.warning(f"Attempt to update invalid/disallowed file: {filename_to_update}")
            return redirect(url_for('display_md_files'))

        # Basic sanitization: replace null bytes
        safe_content = new_content.replace('\x00', '')
        with open(filename_to_update, 'w', encoding='utf-8') as f:
            f.write(safe_content)
        flash(f'{filename_to_update} updated successfully.', 'success')
        logger.info(f"Updated {filename_to_update} via web interface.")
    except Exception as e:
        flash(f'Error updating {filename_to_update}: {e}', 'error')
        logger.error(f"Error writing {filename_to_update}: {e}")

    return redirect(url_for('display_md_files'))

# --- End Multi-MD File Editor Page ---

# --- Thumbnail Generation Route --- 
@app.route('/thumbnail/<path:file_path>')
def serve_thumbnail(file_path):
    """Generates (if needed) and serves a thumbnail for an image."""
    
    # --- Security Check (Similar to download_file) ---
    # Correctly join the file_path with the configured root directory
    indexed_root = os.path.abspath(current_app.config['INDEXED_ROOT_DIR'])
    safe_original_path = os.path.abspath(os.path.join(indexed_root, file_path))
    
    # Ensure the resolved path is still within the indexed root directory
    if not safe_original_path.startswith(indexed_root + os.sep):
        logger.warning(f"Attempt to access file outside allowed directory for thumbnail: {safe_original_path} (resolved from {file_path})")
        abort(403)

    if not os.path.isfile(safe_original_path):
        logger.warning(f"Original image not found for thumbnail: {safe_original_path}")
        abort(404)
        
    # --- Thumbnail Path --- 
    cache_dir = current_app.config['THUMBNAIL_CACHE_DIR']
    # Create a safe filename for the cache (replace slashes, etc.)
    # Using the relative path helps avoid collisions from different base dirs if config changes
    relative_path = os.path.relpath(safe_original_path, current_app.config['INDEXED_ROOT_DIR'])
    cache_filename_base = re.sub(r'[^a-zA-Z0-9_.-]', '_', relative_path)
    # Add a suffix to distinguish it as a thumbnail
    cache_filename = f"{cache_filename_base}_thumb.jpg" # Save as JPG for consistency
    thumbnail_path = os.path.join(cache_dir, cache_filename)

    # --- Generate if needed --- 
    if not os.path.exists(thumbnail_path):
        os.makedirs(cache_dir, exist_ok=True) # Ensure cache dir exists
        try:
            logger.info(f"Generating thumbnail for {safe_original_path} at {thumbnail_path}")
            img = Image.open(safe_original_path)
            # Handle potential transparency (convert to RGB before saving as JPG)
            if img.mode in ("RGBA", "P"): 
                img = img.convert("RGB")
            img.thumbnail(current_app.config['THUMBNAIL_SIZE'])
            img.save(thumbnail_path, "JPEG") # Save as JPEG
        except UnidentifiedImageError:
            logger.error(f"Cannot identify image file (possibly unsupported format): {safe_original_path}")
            # Optionally, serve a placeholder 'cannot display' image here
            abort(404) # Treat as not found for simplicity now
        except Exception as e:
            logger.error(f"Error generating thumbnail for {safe_original_path}: {e}")
            # Log the error but maybe still abort 500? Or serve placeholder?
            abort(500)
            
    # --- Serve Thumbnail --- 
    try:
        return send_file(thumbnail_path, mimetype='image/jpeg')
    except Exception as e:
        logger.error(f"Error sending thumbnail file '{thumbnail_path}': {e}")
        abort(500)
# --- End Thumbnail Route --- 

@app.route('/tests')
def show_tests():
    """Displays a list of discovered unit tests with section navigation."""
    test_data_list = [] # Changed from dict to list of dicts
    page_nav_items = [] # For floating nav
    test_dir = 'tests'
    try:
        test_files = sorted(glob.glob(os.path.join(test_dir, 'test_*.py')))
        
        if not test_files:
            logger.warning("No test files found matching 'tests/test_*.py'")
            # Optional: flash a message?

        for test_file_path in test_files:
            test_filename = os.path.basename(test_file_path)
            file_id = sanitize_for_id(test_filename) # Generate ID
            tests_in_file = []
            error_parsing = False
            try:
                with open(test_file_path, 'r', encoding='utf-8') as f: # Ensure encoding
                    source_code = f.read()
                    tree = ast.parse(source_code)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                            tests_in_file.append(node.name)
            except Exception as e:
                logger.error(f"Error parsing test file {test_filename}: {e}")
                tests_in_file = ["Error parsing file"] # Indicate error
                error_parsing = True

            # Add data for the template section
            test_data_list.append({
                'filename': test_filename,
                'tests': tests_in_file,
                'id': file_id,
                'error': error_parsing
            })
            # Add item for the floating navigation menu
            page_nav_items.append({
                'text': test_filename,
                'href': f'#{file_id}'
            })
                
    except Exception as e:
        logger.error(f"Error accessing test directory or files: {e}")
        flash(f"Error retrieving test files: {e}", "error")
        # test_data_list and page_nav_items will be empty, template handles this
            
    return render_template('tests.html', 
                           test_data=test_data_list, # Pass the list
                           page_nav_items=page_nav_items) # Pass nav items

if __name__ == '__main__':
    print("Starting Flask web server...")
    # Access config via the app object here, not current_app
    print("Ensure the database '{}' exists (run indexer.py first).".format(app.config['DATABASE']))
    print("Access the application at http://127.0.0.1:5000")
    # Use debug=False to reduce memory usage and prevent OOM kills
    app.run(debug=False, host='0.0.0.0') # Host 0.0.0.0 makes it accessible on network 