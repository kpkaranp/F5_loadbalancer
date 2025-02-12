import os
import sys
import base64
from github import Github

# Read arguments
repo_list_file = sys.argv[1]
file_path = sys.argv[2]

# GitHub Token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
github = Github(GITHUB_TOKEN)

# Read repo list
with open(repo_list_file, "r") as file:
    repos = [line.strip() for line in file if line.strip()]

report_lines = []
for repo_name in repos:
    try:
        repo = github.get_repo(repo_name)
        file = repo.get_contents(file_path)
        file_content = base64.b64decode(file.content).decode("utf-8")

        for i, line in enumerate(file_content.splitlines(), start=1):
            if "version =" in line:
                report_lines.append(f"{repo_name} | {file_path} | Line {i} | {line.strip()}")

    except Exception as e:
        report_lines.append(f"{repo_name} | ERROR: {e}")

# Save to file
report_file = "terraform_versions_report.txt"
with open(report_file, "w") as f:
    f.write("\n".join(report_lines))

print("Report generated: {report_file}")
