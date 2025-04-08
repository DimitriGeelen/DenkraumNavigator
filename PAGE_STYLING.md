# Page Styling Notes

This file consolidates notes related to CSS, layout, and visual styling for the DenkraumNavigator project.

## General Styling

*   Global styles are primarily defined in `static/css/style.css`.

## Adding New Pages

*   **Main Navigation:** When adding a new page that should be accessible from the main site navigation, you MUST update `menu.md` by adding a new line in the format `- Link Text: flask_endpoint_name`.
*   **Top Navbar Inclusion:** Ensure the new page's template inherits from `base.html` (or directly includes the navbar component, like `{% include '_navbar.html' %}` if not inheriting) so that the standard top navigation bar is displayed.
*   **Floating Section Navigation:** If the new page contains distinct sections that would benefit from the floating navigation menu (similar to the `/history` or `/md_files` pages), follow the pattern described in the "Floating Page Navigation (Sections)" section below (generating IDs in the backend, passing nav items to the template, etc.).

## Navbar Styling

*   The top navigation bar is dynamically generated based on `menu.md` and styled via `static/css/style.css`.

### Top Navbar Styling Issue & Solution (Previous Issue - Kept for historical context)

*   **Problem:** Applying global styles directly to common HTML elements like `<li>` (e.g., setting a `background` or `padding`) caused unexpected visual bugs in the top navigation bar. Specifically, the navbar links (`<a>` tags inside `<li>` tags) inherited or were affected by the general `<li>` styles, making them appear as boxes instead of plain text links, even when `.navbar a` styles were set correctly.
*   **Solution (Applied before switching to dynamic menu):**
    1.  **Avoid Global Styles on Generic Elements:** Do not apply backgrounds, borders, or significant padding directly to generic selectors like `li` if those elements are used in structurally different components (like navbars and content lists).
    2.  **Use Specific Selectors for Content:** For styling list items within the main content area (e.g., backup lists, version lists), apply styles using a more specific selector. Add a class (e.g., `content-list`) to the parent `<ul>` and target the list items with `.content-list li`.
    3.  **Explicitly Reset Component Styles:** For components like the navbar, explicitly define styles for its child elements (e.g., `.navbar li`) to reset any potentially inherited properties (like `padding`, `border`, `background`, `display`) to ensure they don't interfere with the intended appearance.

## Floating Page Navigation (Sections)

*   Used on `/history` and `/md_files` pages.
*   Relies on the CSS class `.page-nav-links` (defined in `static/css/style.css`) for positioning and appearance.
*   JavaScript in `static/js/scripts.js` handles the toggle button (`#toggle-page-nav`).
*   Requires target sections on the page to have unique `id` attributes for the links (`#section-id`) to work.

## CSS Learnings / Best Practices

*   **CSS Scoping:** CSS rules defined within a `<style>` block in one template (`templates/history.html` previously) are not automatically available in other templates. Avoid page-specific `<style>` blocks for reusable components. **Solution:** Move shared styles (e.g., `.btn-link`, `.btn-link-download-db`, etc.) to the global stylesheet (`static/css/style.css`).
*   **Browse Page Styles:** Styles for breadcrumbs (`.breadcrumbs`) and the directory/file listing (`.browser-list`, `.item-name`, etc.) were moved from an inline `<style>` block in `templates/browse.html` to `static/css/style.css`. 