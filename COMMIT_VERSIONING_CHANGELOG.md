# Commit, Versioning, and Changelog Workflow

This document outlines the standard process for making commits, bumping versions, and updating the changelog for the DenkraumNavigator project.

## Commit & Versioning Workflow

**Important Note (AI Assistant Interaction):** When instructing the AI assistant to perform a commit using the terminal tool, avoid using multi-line commit messages within the `-m "..."` flag. Use a single-line message instead, or the command may fail.

1.  **Run Unit Tests:** Before committing functional changes, run `pytest -v`. Fix any failures.
2.  **Stage Changes:** Stage the functionally complete changes (`git add .` or specific files).
3.  **Commit Functional Changes:** Commit with a conventional commit message (`git commit -m "type: Description"`).
4.  **Verify Hook:** Observe terminal output to ensure the post-commit hook created `commit_<hash>.db` and `commit_<hash>.zip` backups successfully.
5.  **(Manual) Decide Version Bump:** Determine if the committed changes warrant a version increment (patch, minor, major).
6.  **(Manual or Scripted) Update Version File & Changelog:** If bumping version:
    *   **(Option A - Manual):**
        *   **Fetch Recent Commits:** Use `git log <last_tag>..HEAD --pretty=format:"- %s (%h)"` (replacing `<last_tag>` with the relevant previous tag, e.g., last minor for a minor bump, last major for a major bump) to get a summary of changes since the last version tag.
        *   Edit the `VERSION` file (e.g., increment `1.2.0` to `1.2.1` or `1.3.0`).
        *   Add release notes to `CHANGELOG.md`, incorporating the summary of commits fetched above.
    *   **(Option B - Scripted):**
        *   Run `python version_bumper.py --patch | --minor | --major`. This script handles fetching commits, updating `VERSION` and `CHANGELOG.md`, committing, and tagging automatically.
7.  **(Conditional - Manual Only) Stage Version Files:** If using Option A in step 6, stage the files: `git add VERSION CHANGELOG.md`.
8.  **(Conditional - Manual Only) Commit Version Update:** If using Option A in step 6, commit the version bump (`git commit -m "chore: Bump version to x.y.z"`). Verify the hook runs again.
9.  **(Conditional - Manual Only) Tag Version Commit:** If using Option A in step 6, tag the *version commit* with the corresponding version number (`git tag vx.y.z`).
10. **(Optional) Push:** Push commits and tags to remote (`git push origin <branch> --tags`).

*Note: Backups are primarily named by commit hash. Tags link semantic versions (vX.Y.Z) to specific commits (and thus their hash-named backups) in the Git history.*

## Related Files

*   `VERSION`: Stores the current version number.
*   `CHANGELOG.md`: Records version release notes.
*   `.git/hooks/post-commit`: The script that creates backups after each commit.
*   `version_bumper.py`: Script to automate steps 6-9 for version bumps. 