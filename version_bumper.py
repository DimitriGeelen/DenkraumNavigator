import argparse
import os
import sys
import datetime

try:
    import semver
except ImportError:
    print("Error: 'semver' library not found. Please install it: pip install semver")
    sys.exit(1)

VERSION_FILE = "VERSION"
CHANGELOG_FILE = "CHANGELOG.md"

def get_current_version():
    """Reads the version from the VERSION file."""
    if not os.path.exists(VERSION_FILE):
        print(f"Error: {VERSION_FILE} not found.")
        sys.exit(1)
    with open(VERSION_FILE, 'r') as f:
        version_str = f.read().strip()
    try:
        return semver.VersionInfo.parse(version_str)
    except ValueError:
        print(f"Error: Invalid version format '{version_str}' in {VERSION_FILE}. Use format X.Y.Z.")
        sys.exit(1)

def update_version_file(new_version):
    """Writes the new version to the VERSION file."""
    with open(VERSION_FILE, 'w') as f:
        f.write(str(new_version))
    print(f"Updated {VERSION_FILE} to {new_version}")

def update_changelog(new_version, old_version):
    """Adds a new version header to CHANGELOG.md."""
    if not os.path.exists(CHANGELOG_FILE):
        print(f"Warning: {CHANGELOG_FILE} not found. Cannot update.")
        return

    try:
        with open(CHANGELOG_FILE, 'r') as f:
            lines = f.readlines()

        # Find the [Unreleased] header
        unreleased_line_index = -1
        for i, line in enumerate(lines):
            if line.strip() == "## [Unreleased]":
                unreleased_line_index = i
                break
        
        if unreleased_line_index == -1:
            print(f"Warning: '## [Unreleased]' header not found in {CHANGELOG_FILE}. Cannot update automatically.")
            return
        
        # Find the first version header below [Unreleased]
        first_version_line_index = -1
        for i in range(unreleased_line_index + 1, len(lines)):
            if lines[i].strip().startswith("## ["):
                first_version_line_index = i
                break
        
        if first_version_line_index == -1:
             first_version_line_index = len(lines) # Add at the end if no previous versions

        today = datetime.date.today().strftime("%Y-%m-%d")
        new_version_header = f"## [{new_version}] - {today}"
        
        # Prepare lines to insert
        insert_lines = [
            "\n", # Blank line before new version
            new_version_header + "\n",
            "### Added\n",
            "- (Add your changes here)\n",
            "\n", # Blank line after section
        ]
        
        # Insert the new version section before the previous version (or at the end)
        lines[first_version_line_index:first_version_line_index] = insert_lines

        # Update the [Unreleased] comparison link
        unreleased_link_line = f"[Unreleased]: https://github.com/DimitriGeelen/DenkraumNavigator/compare/v{new_version}...HEAD\n"
        # Find and replace the old Unreleased link line
        link_section_start = -1
        for i in range(len(lines) -1, -1, -1): # Search backwards for link section
             if lines[i].strip().startswith("["):
                 link_section_start = i
                 break
             if lines[i].strip() == "": # Stop if we hit a blank line before finding links
                 break

        if link_section_start != -1:
            updated_link_section = False
            for i in range(link_section_start, len(lines)):
                if lines[i].startswith("[Unreleased]:"):
                    lines[i] = unreleased_link_line
                    updated_link_section = True
                    break
            if not updated_link_section:
                 # Add it if not found
                 lines.append(unreleased_link_line)
        else:
            lines.append(unreleased_link_line) # Add link if no link section found
        
        # Add the link definition for the new version
        new_version_link_line = f"[{new_version}]: https://github.com/DimitriGeelen/DenkraumNavigator/compare/v{old_version}...v{new_version}\n"
        lines.append(new_version_link_line)

        with open(CHANGELOG_FILE, 'w') as f:
            f.writelines(lines)
        
        print(f"Updated {CHANGELOG_FILE} with header for {new_version}")
        print(f"NOTE: Please manually edit {CHANGELOG_FILE} to add detailed changes for version {new_version}.")

    except Exception as e:
        print(f"Error updating {CHANGELOG_FILE}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Bump the version in the VERSION file and update CHANGELOG.md.")
    parser.add_argument("part", choices=["major", "minor", "patch"], 
                        help="The part of the version to bump (major, minor, or patch).")
    
    args = parser.parse_args()
    
    current_version = get_current_version()
    
    if args.part == "major":
        new_version = current_version.bump_major()
    elif args.part == "minor":
        new_version = current_version.bump_minor()
    elif args.part == "patch":
        new_version = current_version.bump_patch()
    else:
        # Should be unreachable due to argparse choices
        print(f"Error: Invalid part '{args.part}'.") 
        sys.exit(1)
        
    print(f"Current version: {current_version}")
    print(f"Bumping {args.part} version...")
    
    update_version_file(new_version)
    update_changelog(new_version, current_version) # Pass old version for link generation

if __name__ == "__main__":
    main() 