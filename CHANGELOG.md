# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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