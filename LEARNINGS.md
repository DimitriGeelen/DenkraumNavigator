# Project Learnings

Record key learnings, insights, and reflections during the project here.

- **Gunicorn Caching/Process Management:** Gunicorn can sometimes serve stale versions of the application code, especially if it's preloading the app or if old worker processes aren't terminated correctly. This led to `NameError`s for variables defined in newer code. Solution involved forcefully killing old Gunicorn processes (`pkill -f gunicorn`) and clearing Python bytecode cache (`rm -rf __pycache__`) in the restart script (`restart_server.sh`) to ensure the latest code is loaded.
- **Jinja Template Syntax Errors:** Commenting out blocks of HTML containing Jinja tags (like `{% if %}`/`{% endif %}`) using HTML comments (`<!-- ... -->`) does *not* prevent Jinja from parsing those tags. This caused a `TemplateSyntaxError` (unexpected 'endif'). Solution was to completely delete the commented-out block from the template (`templates/index.html`) or use Jinja comments (`{# ... #}`).
- **Jinja Variable Mismatches:** When using conditional logic (e.g., `{% if ... %}`) in templates based on data from the backend, ensure the values being compared *exactly* match (including case and formatting). We encountered an issue where the template checked for lowercase short types (`pdf`, `word`) while the backend provided full names (`PDF Document`, `Word Document`), causing the logic to fail. Solution was to update the template conditions to match the backend data.
- **Flask `url_for()` vs. URL Paths:** When dynamically generating URLs for navigation (like from `menu.md`), ensure the source file provides the correct Flask *endpoint names* (function names decorated with `@app.route`) and not just URL *paths*. Using paths (e.g., `/history`) with `url_for()` will cause it to fail (often silently in the browser, check Flask logs), leading to missing links/elements. Solution: Use the correct endpoint names (e.g., `history`) in the source data (`menu.md`).
- **Dynamic Floating Page Navigation:** To implement a floating navigation menu (like on `/history` and `/md_files`) for dynamically generated page sections:
    1.  **Backend (`app.py`):** In the route function, when preparing the data for the main page sections (e.g., a list of files/items), generate a unique, sanitized HTML ID for each section (e.g., based on filename or item key). Store this ID alongside the item's data.
    2.  **Backend (`app.py`):** Create a separate list of navigation items. Each item should contain the display text (e.g., filename) and the `href` value (e.g., `f'#{sanitized_id}'`). Pass this navigation list to the template.
    3.  **Template (`.html`):** Render the main page sections using a loop. Add the `id="{{ item.id }}"` attribute to the container element of each section, using the ID generated in the backend.
    4.  **Template (`.html`):** Add the HTML structure for the floating menu (e.g., `<div class="page-nav-links">...</ul>`). Inside the `<ul>`, loop through the navigation item list passed from the backend and render the `<li><a href="{{ nav_item.href }}">{{ nav_item.text }}</a></li>` elements.
    5.  **CSS/JS:** Ensure the necessary CSS for styling/positioning the floating menu and the JavaScript for any toggle functionality are linked and applied.
- **Robust Gunicorn Restart:** When Gunicorn fails to shut down cleanly, relying solely on `kill <PID>` from a PID file can be insufficient, leading to "Address already in use" errors. A more robust approach in restart scripts (`restart_server_prod.sh`) is to:
    1.  Attempt graceful shutdown using the PID file (`kill -TERM <PID>`).
    2.  Wait and check if the process is gone (`ps -p <PID>`).
    3.  If still running, force kill (`kill -KILL <PID>`).
    4.  Regardless of PID file success, check if the port is actually free using `fuser <PORT>/tcp`.
    5.  If the port is still in use, use `fuser -k -TERM <PORT>/tcp` for a graceful kill.
    6.  If still in use after a pause, use `fuser -k -KILL <PORT>/tcp` for a forceful kill.
    7.  Include pauses (`sleep`) after kill attempts to allow the OS time to release the port.
- 