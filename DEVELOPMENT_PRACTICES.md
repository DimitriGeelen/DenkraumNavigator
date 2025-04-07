# Development Practices

*   **Run Unit Tests:** Run unit tests (`pytest -v`) and ensure they pass before *every* commit. Fix any failures before proceeding.
*   **Add Unit Tests:** Always add unit tests for new functionality.
*   **Script Permissions:** Ensure any new shell scripts (`.sh`) are made executable (`chmod +x <script_name>.sh`).
*   **Frequent Commits:** Commit changes after each significant task completion or prompt that results in code/documentation modifications. Follow the `COMMIT_VERSIONING_CHANGELOG.md` workflow when applicable (e.g., for features, fixes). 