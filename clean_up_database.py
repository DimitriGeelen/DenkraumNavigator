import sqlite3
import os
import sys
import logging
from tqdm import tqdm

# --- Configuration ---
DATABASE_NAME = os.environ.get('DENKRAUM_DB_FILE', 'file_index.db') # Use env var or default
LOG_FILE = 'database_cleanup.log'
COMMIT_INTERVAL = 500 # Commit after every N deletions

# --- Logging Setup ---
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main Function ---
def clean_database(db_name=DATABASE_NAME):
    """Scans the database for non-existent file paths and removes them."""
    print(f"--- Starting Database Cleanup for '{db_name}' ---")
    logging.info(f"Starting database cleanup for {db_name}")

    conn = None
    try:
        conn = sqlite3.connect(db_name, timeout=30)
        cursor = conn.cursor()
        print("Fetching all file paths from the database...")
        cursor.execute("SELECT id, path FROM files")
        all_rows = cursor.fetchall()
        total_rows = len(all_rows)
        print(f"Found {total_rows} entries to check.")

        if total_rows == 0:
            print("Database is empty. No cleanup needed.")
            logging.info("Database is empty. No cleanup needed.")
            return

        ids_to_delete = []
        deleted_count = 0
        checked_count = 0

        print("Checking file existence...")
        with tqdm(total=total_rows, unit='file', desc="Checking paths") as pbar:
            for row_id, file_path in all_rows:
                checked_count += 1
                if not os.path.exists(file_path):
                    ids_to_delete.append(row_id)
                    logging.info(f"Marking for deletion (File not found): ID={row_id}, Path={file_path}")
                    # Commit periodically if we accumulate enough deletions
                    if len(ids_to_delete) >= COMMIT_INTERVAL:
                        print(f"\nCommitting deletion batch ({len(ids_to_delete)} entries)...")
                        delete_sql = f"DELETE FROM files WHERE id IN ({','.join(['?']*len(ids_to_delete))})"
                        cursor.execute(delete_sql, ids_to_delete)
                        conn.commit()
                        deleted_count += len(ids_to_delete)
                        print(f"Committed. Total deleted so far: {deleted_count}")
                        ids_to_delete = [] # Reset batch
                pbar.update(1)

        # Delete any remaining marked IDs
        if ids_to_delete:
            print(f"\nCommitting final deletion batch ({len(ids_to_delete)} entries)...")
            delete_sql = f"DELETE FROM files WHERE id IN ({','.join(['?']*len(ids_to_delete))})"
            cursor.execute(delete_sql, ids_to_delete)
            conn.commit()
            deleted_count += len(ids_to_delete)
            print("Committed.")

        print("\n--- Cleanup Summary ---")
        print(f"Total entries checked: {checked_count}")
        print(f"Entries deleted (file not found): {deleted_count}")
        logging.info(f"Cleanup finished. Checked: {checked_count}, Deleted: {deleted_count}")

    except sqlite3.Error as e:
        print(f"\nDatabase error during cleanup: {e}", file=sys.stderr)
        logging.error(f"Database error during cleanup: {e}", exc_info=True)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        logging.error(f"Unexpected error during cleanup: {e}", exc_info=True)
        traceback.print_exc()
    finally:
        if conn:
            print("Closing database connection.")
            conn.close()
            logging.info("Database connection closed.")

# --- Main Execution ---
if __name__ == "__main__":
    # Allow specifying DB file as argument, otherwise use default/env var
    db_to_clean = sys.argv[1] if len(sys.argv) > 1 else DATABASE_NAME
    clean_database(db_to_clean)
    print("Cleanup script finished.") 