# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial commit history and backup download functionality.
- Browse archive functionality.
- Manual DB backup creation.
- Automatic commit-based DB and Code backups via post-commit hook.
- Database restore functionality (from History page).
- Pytest testing framework with tests for backup/restore and search.
- VERSION file and CHANGELOG.md.
- Commit & Versioning workflow documentation.

### Changed
- Refactored app.py to use app.config for paths (DB, Backups, Indexed Root).

### Fixed
- Navbar styling consistency on history page.
- Startup error when using `current_app` outside context.
- Post-commit hook failures (shebang, git archive exclusions).
- Unit test failures (backup dir path, flash message checking, status codes).

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