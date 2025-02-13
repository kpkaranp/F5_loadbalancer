import os
import re
import sys
import base64
from github import Github

GITHUB_ENTERPRISE_URL = "https://github.axa.com/api/v3"


# Read arguments from system
if len(sys.argv) < 5:
    print("Usage: python tfe_module_update.py <repo_list.txt> <file_path> <old_version> <new_version>")
    sys.exit(1)

repo_list_file = sys.argv[1]  # File containing repo names (one per line)
file_path = sys.argv[2]  # Path to Terraform file in repo
old_version = sys.argv[3]  # Old version string
new_version = sys.argv[4]  # New version string

# GitHub Token (Store in environment variable)
GITHUB_TOKEN = ""

if not GITHUB_TOKEN:
    print("ERROR: Missing GITHUB_TOKEN. Set it using `export GITHUB_TOKEN=your_token`")
    sys.exit(1)

# Authenticate with GitHub
#github = Github(GITHUB_TOKEN)
github = Github(base_url=GITHUB_ENTERPRISE_URL, login_or_token=GITHUB_TOKEN)
# Read repository names from file
with open(repo_list_file, "r") as file:
    repos = [line.strip() for line in file if line.strip()]

for repo_name in repos:
    print(repo_name)
    try:
        print(f"Processing repo: {repo_name}")
        repo = github.get_repo(repo_name)

        # Get the file contents
        file = repo.get_contents(file_path)
        file_content = base64.b64decode(file.content).decode("utf-8")
        print(file_content) 
        # Check if version needs update
        if old_version in file_content:
            new_content = re.sub(old_version, new_version, file_content)

            # Commit the change
            repo.update_file(
                file.path, 
                "Update Terraform version from {old_version} to {new_version}", 
                new_content, 
                file.sha
            )
            print(f"Updated {repo_name}/{file.path}")

        else:
            print(f"No changes needed in {repo_name}")

    except Exception as e:
        print(f"Failed to update {repo_name}: {e}")
