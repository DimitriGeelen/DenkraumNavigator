import sqlite3
import argparse
import sys
import os

DATABASE_NAME = 'file_index.db'

def search_files(args):
    """Connects to the DB and performs search based on arguments."""
    if not os.path.exists(DATABASE_NAME):
        print(f"Error: Database file '{DATABASE_NAME}' not found.", file=sys.stderr)
        print("Please run the indexer script first.", file=sys.stderr)
        sys.exit(1)

    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        # Optional: Use Row factory for dict-like access
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # --- Build SQL Query ---
        base_query = "SELECT path, filename, category_type, category_year, summary, keywords FROM files WHERE 1=1"
        conditions = []
        params = []

        if args.filename:
            conditions.append("filename LIKE ?")
            params.append(f"%{args.filename}%") # Wildcard search

        if args.year:
            conditions.append("category_year = ?")
            params.append(args.year)

        if args.type:
            conditions.append("LOWER(category_type) = LOWER(?)")
            params.append(args.type)

        if args.keywords:
            keyword_list = [kw.strip() for kw in args.keywords.split(',') if kw.strip()]
            keyword_conditions = []
            for kw in keyword_list:
                # Search in both keywords and summary for broader matching
                keyword_conditions.append("(keywords LIKE ? OR summary LIKE ?)")
                params.extend([f"%{kw}%", f"%{kw}%"])
            if keyword_conditions:
                 # Combine multiple keywords with AND
                conditions.append(f"({' AND '.join(keyword_conditions)})")

        if not conditions:
            print("Error: Please provide at least one search criterion.", file=sys.stderr)
            parser.print_help()
            sys.exit(1)

        sql_query = f"{base_query} AND {' AND '.join(conditions)}"
        # print(f"DEBUG SQL: {sql_query}") # Uncomment for debugging
        # print(f"DEBUG PARAMS: {params}")

        # --- Execute Query ---
        cursor.execute(sql_query, params)
        results = cursor.fetchall()

        # --- Display Results ---
        if not results:
            print("No files found matching your criteria.")
        else:
            print(f"Found {len(results)} matching files:")
            print("-" * 30)
            for i, row in enumerate(results):
                print(f"Result {i+1}:")
                print(f"  Path:     {row['path']}")
                print(f"  Type:     {row['category_type']}")
                print(f"  Year:     {row['category_year']}")
                # Limit summary/keywords display length if needed
                summary_display = (row['summary'][:200] + '...') if row['summary'] and len(row['summary']) > 200 else row['summary']
                print(f"  Summary:  {summary_display or 'N/A'}")
                print(f"  Keywords: {row['keywords'] or 'N/A'}")
                print("-" * 30)

    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search the file index.")

    parser.add_argument("-f", "--filename", type=str, help="Search by filename pattern (e.g., 'report', '*.docx').")
    parser.add_argument("-y", "--year", type=int, help="Filter by year (last modified).")
    parser.add_argument("-t", "--type", type=str, help="Filter by file type (e.g., 'PDF Document', 'Image'). Case-insensitive.")
    parser.add_argument("-k", "--keywords", type=str, help="Search for keywords (comma-separated) within summary or keywords field.")
    # Add more arguments as needed (e.g., date range, size)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    search_files(args) 