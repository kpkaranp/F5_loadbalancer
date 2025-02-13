import os
import re
import sys
import base64
from github import Github # PyGithub
from dotenv import load_dotenv # python-dotenv
from urllib.parse import urlparse

def check_arguments():
    if len(sys.argv) < 5:
        print("Usage: python update_terraform.py <repo_list.txt> <file_path> <old_version> <new_version>")
        sys.exit(1)
    
    return (sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

def extract_version(version_str):
    """Extract version number from a version string."""
    match = re.search(r'"([^"]+)"', version_str)
    if match:
        return match.group(1)
    return version_str

def initialize_github_client():
    """Initialize GitHub client based on environment configuration."""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("ERROR: Missing GITHUB_TOKEN in .env file")
        sys.exit(1)

    # Check if enterprise GitHub URLs are provided
    github_base_url = os.getenv("GITHUB_BASE_URL")
    github_api_url = os.getenv("GITHUB_API_URL")

    if github_base_url and github_api_url:
        # Enterprise GitHub
        print(f"Using Enterprise GitHub: {github_base_url}")
        return Github(
            base_url=github_api_url,
            login_or_token=github_token
        )
    else:
        # Public GitHub.com
        print("Using Public GitHub.com")
        return Github(github_token)

def update_terraform_version(content, old_version_str, new_version_str):
    updated_content = []
    changes_made = False
    
    # Extract version numbers from the strings
    old_version = extract_version(old_version_str)
    new_version = extract_version(new_version_str)
    
    # Split content into lines for line-by-line processing
    lines = content.split('\n')
    
    for line in lines:
        original_line = line
        
        # Check for version patterns in Terraform files
        if 'version' in line.lower():
            # Simple direct string replacement
            if f'"{old_version}"' in line:
                new_line = line.replace(f'"{old_version}"', f'"{new_version}"')
                if new_line != original_line:
                    line = new_line
                    changes_made = True
        
        updated_content.append(line)
    
    return '\n'.join(updated_content), changes_made

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get and validate inputs
    repo_list_file, file_path, old_version, new_version = check_arguments()
    
    # Initialize appropriate GitHub client
    github = initialize_github_client()
    
    # Read repository names from file
    try:
        with open(repo_list_file, "r") as file:
            repos = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Error: Repository list file '{repo_list_file}' not found")
        sys.exit(1)
    
    # Process each repository
    for repo_name in repos:
        try:
            print(f"\nProcessing repo: {repo_name}")
            repo = github.get_repo(repo_name)
            
            try:
                file = repo.get_contents(file_path)
            except Exception as e:
                print(f"Error: Could not find file {file_path} in {repo_name}: {str(e)}")
                continue
                
            file_content = base64.b64decode(file.content).decode("utf-8")
            
            # Update version and check if changes were made
            new_content, changes_made = update_terraform_version(file_content, old_version, new_version)
            
            if changes_made:
                try:
                    commit_message = f"Update Terraform version from {extract_version(old_version)} to {extract_version(new_version)}"
                    repo.update_file(
                        file.path,
                        commit_message,
                        new_content,
                        file.sha
                    )
                    print(f"✅ Successfully updated {repo_name}/{file_path}")
                except Exception as e:
                    print(f"❌ Failed to commit changes to {repo_name}: {str(e)}")
            else:
                print(f"ℹ️ No version updates needed in {repo_name}/{file_path}")
                
        except Exception as e:
            print(f"❌ Error processing {repo_name}: {str(e)}")

if __name__ == "__main__":
    main()
