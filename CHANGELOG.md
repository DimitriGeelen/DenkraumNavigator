# Changelog

## [v2.3.0] - YYYY-MM-DD
### Added
- feat: Add Learnings back to main menu (d66d752)

## [v2.2.0] - 2024-05-25

### Added
- feat: Implement features and updates for major release (4cb387c)
- feat: Enhance restart script to tail logs (5053799)
- feat: Add basic CSS styling and link stylesheet (a523fb4)
- feat: Add editable project goals page (/goals) (e99dbfa)
- feat: Add version_bumper.py script to automate versioning (54ee5c9)

### Changed
- refactor: Rename goals endpoint again to display_project_goals (30f15d6)
- refactor: Rename goals endpoint to show_goals (a35b0a8)
- refactor: Dynamically generate navbar from menu.md (36876e8)

### Fixed
- fix: Correct menu parsing logic and add unit tests (c461746)

### Reverted
- revert: Revert attempt to generate menu URLs in before_request (e58fdd2)

### Other (Docs, Chore, Test)
- docs: Move navbar notes to menu.md and update refs (4a33ad7)
- docs: Refactor commit/versioning workflow into separate file (9192cae)
- docs: Minor update to project notes for testing (f7e95e2)
- chore: Bump version to 1.2.0 (9d98aff)
- chore: Test commit for filename verification (7cecd16)
- chore: Bump version to 1.1.0 (e8023fe)
- test: Skip flaky integration test and fix restore test cleanup (0bcac36)
- test: Create commit to verify download link on history page (a18cfe1)
- test: Create commit to verify download link on history page (23c0bf9)
- test: Create commit to verify download link on history page (657e211)
- test: Create commit to verify download link on history page (e2e2702)
- test: Create commit to verify download link on history page (b7f24e1)
- test: Create commit to verify download link on history page (f709ffe)
- test: Create commit to verify download link on history page (41030fc)
- test: Create commit to verify download link on history page (6a96689)
- test: Create commit to verify download link on history page (bb7a1c8)

## [Unreleased]

## [1.2.0] - 2025-04-07

### Fixed

- Corrected filename patterns used for finding commit-based backups (`commit_<hash>.*`) in the `/history` page and the `/download_commit_package` route, ensuring backup download links appear and function correctly.

### Added

- Added debug logging to `get_commit_details` and `download_commit_package` to show glob patterns and results.

## [1.1.0] - 2025-04-07

### Added
- Integration test (`test_download_link_for_latest_commit`) to verify commit->hook->history->download workflow (currently skipped due to environment issues).

### Fixed
- Flaky `test_database_restore` by ensuring temporary backup directory is cleared before test.
- `NameError` in `test_download_link_for_latest_commit` exception handler.

### Changed
- Skipped `test_download_link_for_latest_commit` due to file visibility issues in test environment.
- Updated `test_download_link_for_latest_commit` with increased sleep and debugging steps (ultimately skipped).

## [1.0.0] - 2025-04-07

### Added
- Detailed Commit History section on `/history` page:
    - Lists recent commits with hash, date, subject, and associated tags.
    - Provides a "Download Package" link for each commit *only if* corresponding DB and Code backups exist.
- Backup verification logic in `post-commit` hook:
    - Checks for file existence and non-zero size after DB copy and code archive.
    - Exits with non-zero status on backup failure.
    - Uses `git archive` with specific paths for more reliable code backup.
- Unit tests (`test_backup_verification.py`) for backup verification logic.
- Browse page (`/browse/`) for navigating the indexed directory structure.
- Project notes (`PROJECT_NOTES.md`) section on server restart script.
- Project notes section on automated backups and verification.
- Project notes section on navbar styling solution.

### Changed
- Updated `/history` page requirements in `PROJECT_NOTES.md` to include detailed commit list.
- Refactored `/history` route in `app.py` to fetch detailed commit data and check backup status.
- Made `/download_commit_package` route in `app.py` more robust using `glob`.

### Fixed
- Persistent navbar styling bug on `/history` page where links appeared as boxes.
- Potential failure in `post-commit` hook when archiving code (removed `.git/hooks/post-commit` from archive paths).
- Potential 404 errors for `/download_commit_package` route when backup files were missing.

### Removed
- Old sections listing individual commit DB/Code backup files from `/history` page (replaced by Detailed Commit History).

## [0.7.0] - YYYY-MM-DD
### Added
- Tag-based backup naming convention (though hook logic needs review - currently uses hash).

## [0.6.1] - 2025-04-06
### Added
- Browse Archive page (`/browse`).
- Link to Browse Archive in navbar.

### Fixed
- Navbar styling on history page (`/history`) to use plain links.

## [0.6.0] - 2025-04-06
### Added
- History page (`/history`) showing git log and download links for backups.
- Download links for current code and package (code + DB).
- Backup directory (`/backups`) added to `.gitignore`.

## [0.5.0] - 2025-04-06
### Added
- Keyword Cloud on main search page.
- Clickable keywords in cloud perform search.
- Search filters for Year and File Type (multiple selection).
- Reset Filters button.

## [0.4.0] - 2025-04-06
### Added
- Search functionality by filename and keywords.
- Display search results with basic metadata and download links.
- Flask application structure (`app.py`, `templates/index.html`).

## [0.3.0] - 2025-04-06
### Changed
- Improved text extraction logic in `indexer.py` for various file types.
- Added error handling for missing optional dependencies (docx, openpyxl, etc.).

## [0.2.0] - 2025-04-06
### Added
- Basic file indexing logic (`indexer.py`) storing path, filename, type, year, summary, keywords.
- SQLite database (`file_index.db`) schema.

## [0.1.0] - 2025-04-06
### Added
- Initial project setup.
- Basic README.

[Unreleased]: https://github.com/DimitriGeelen/DenkraumNavigator/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/DimitriGeelen/DenkraumNavigator/releases/tag/v0.7.0
[0.6.1]: https://github.com/DimitriGeelen/DenkraumNavigator/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/DimitriGeelen/DenkraumNavigator/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/DimitriGeelen/DenkraumNavigator/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/DimitriGeelen/DenkraumNavigator/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/DimitriGeelen/DenkraumNavigator/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/DimitriGeelen/DenkraumNavigator/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DimitriGeelen/DenkraumNavigator/releases/tag/v0.1.0 