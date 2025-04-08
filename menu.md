# Main Navigation Menu Items

# Format: - Text: flask_endpoint_name

- Search: index
- Browse: browse
- History & Backups: history
- MD Files: display_md_files
- Unit Tests: show_tests
- Configuration: config_page

## Navbar Styling Notes

*Styling notes, including historical issues and solutions, have been moved to `PAGE_STYLING.md`.*

---

## Debugging Notes

*   **Issue:** Navigation links (specifically "Goals") were missing on the main search page (`index.html`), even though they appeared correctly on other pages (`base.html` derivatives).
*   **Cause:** The `index.html` template contained a *hardcoded* HTML list for its navigation bar, unlike `base.html` which used a dynamic Jinja loop (`{% for item in g.main_menu %}`).
*   **Solution:** Replaced the hardcoded `<ul>...</ul>` in `templates/index.html` with the same dynamic Jinja loop used in `base.html` to ensure consistent menu rendering across all pages. 

*   [Home](/) - Main search and entry point.
*   [Browse](/browse/) - Browse the file structure.
*   [History & Backups](/history) - View version history, tags, commits, and manage backups.
*   [Edit MD Files](/md_files) - Edit root Markdown files.
*   [Unit Tests](/tests) - View discovered unit tests.
*   [Configuration](/config) - View/Update application configuration. 