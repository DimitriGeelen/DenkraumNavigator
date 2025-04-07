# Main Navigation Menu Items

# Format: - Text: flask_endpoint_name

- Search: index
- Browse: browse
- History & Backups: history
- Goals: show_goals

## Navbar Styling Notes (From PROJECT_NOTES.md)

### Top Navbar Styling Issue & Solution (Previous Issue)

*   **Problem:** Applying global styles directly to common HTML elements like `<li>` (e.g., setting a `background` or `padding`) caused unexpected visual bugs in the top navigation bar. Specifically, the navbar links (`<a>` tags inside `<li>` tags) inherited or were affected by the general `<li>` styles, making them appear as boxes instead of plain text links, even when `.navbar a` styles were set correctly.
*   **Solution (Applied before switching to dynamic menu):**
    1.  **Avoid Global Styles on Generic Elements:** Do not apply backgrounds, borders, or significant padding directly to generic selectors like `li` if those elements are used in structurally different components (like navbars and content lists).
    2.  **Use Specific Selectors for Content:** For styling list items within the main content area (e.g., backup lists, version lists), apply styles using a more specific selector. Add a class (e.g., `content-list`) to the parent `<ul>` and target the list items with `.content-list li`.
    3.  **Explicitly Reset Component Styles:** For components like the navbar, explicitly define styles for its child elements (e.g., `.navbar li`) to reset any potentially inherited properties (like `padding`, `border`, `background`, `display`) to ensure they don't interfere with the intended appearance.

*Note: The navbar is now dynamically generated based on this file and styled via `static/css/style.css`. These notes are kept for historical context.* 