import requests
from requests.auth import HTTPBasicAuth
import pandas as pd

# --- Configuration ---
f5_host = 'https://<f5-mgmt-ip>'  # e.g., https://192.168.1.245
username = 'admin'
password = 'your_password'

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

# --- Get all pools ---
def get_pools():
    url = f"{f5_host}/mgmt/tm/ltm/pool"
    response = requests.get(url, auth=HTTPBasicAuth(username, password), verify=False)
    response.raise_for_status()
    return response.json().get('items', [])

# --- Get members for a pool ---
def get_pool_members(pool_name):
    url = f"{f5_host}/mgmt/tm/ltm/pool/{pool_name.replace('/', '~')}/members"
    response = requests.get(url, auth=HTTPBasicAuth(username, password), verify=False)
    response.raise_for_status()
    return response.json().get('items', [])

# --- Main Execution ---
def generate_f5_summary_excel(output_file='f5_pool_summary.xlsx'):
    all_data = []

    pools = get_pools()
    for pool in pools:
        pool_name = pool['fullPath']
        members = get_pool_members(pool_name)
        for member in members:
            all_data.append({
                "Pool": pool_name,
                "Member": member.get('name'),
                "Address": member.get('address', 'N/A'),
                "State": member.get('session', 'unknown'),
                "Availability": member.get('state', 'unknown')
            })

    # Save to Excel
    df = pd.DataFrame(all_data)
    df.to_excel(output_file, index=False)
    print(f"✅ Excel file saved: {output_file}")

# Run it
generate_f5_summary_excel()
