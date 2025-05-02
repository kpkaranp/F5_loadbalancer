import requests
import pandas as pd
from requests.auth import HTTPBasicAuth

# --- F5 Configuration ---
f5_host = 'https://<F5-HOSTNAME_OR_IP>'  # e.g., https://192.168.1.245
username = 'admin'
password = 'your_password'

# --- Setup ---
requests.packages.urllib3.disable_warnings()
auth = HTTPBasicAuth(username, password)
headers = {'Content-Type': 'application/json'}


----------------------------------------------------------------------------------------

    # --- Get all virtual servers ---
    def get_virtual_servers():
        url = f"https://{BIG_IP}/mgmt/tm/ltm/virtual"
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        return response.json().get('items', [])
    
    # --- Get all pools ---
    def get_pools():
        url = f"https://{BIG_IP}/mgmt/tm/ltm/pool"
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        return response.json().get('items', [])
    
    # --- Get members for a pool (by fullPath) ---
    def get_pool_members(pool_full_path):
        pool_uri = pool_full_path.replace('/', '~')  # e.g., Common/pool_web → ~Common~pool_web
        url = f"https://{BIG_IP}/mgmt/tm/ltm/pool/{pool_uri}/members"
        response = requests.get(url, auth=auth, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json().get('items', [])
        return []



all_data = []

# Build virtual server → pool mapping
virtuals = get_virtual_servers()
virtual_map = {}
for vs in virtuals:
    vs_name = vs['name']
    pool = vs.get('pool')  # e.g., "/Common/pool_web"
    if pool:
        pool_name = pool.strip('/').replace('/', '~')  # e.g., Common~pool_web
        virtual_map.setdefault(pool_name, []).append(vs_name)

# Get all pools and their members
pools = get_pools()
for pool in pools:
    pool_full_path = pool['fullPath']  # e.g., "Common/pool_web"
    pool_uri = pool_full_path.replace('/', '~')
    members = get_pool_members(pool_full_path)

    associated_vs_list = virtual_map.get(pool_uri, [])
    vs_names = ', '.join(associated_vs_list) if associated_vs_list else 'Unlinked'

    if members:
        for member in members:
            all_data.append({
                "Virtual Server(s)": vs_names,
                "Pool": pool_full_path,
                "Member": member.get('name'),
                "Address": member.get('address', 'N/A'),
                "Session State": member.get('session', 'unknown'),
                "Availability": member.get('state', 'unknown')
            })
    else:
        all_data.append({
            "Virtual Server(s)": vs_names,
            "Pool": pool_full_path,
            "Member": "No Members",
            "Address": "-",
            "Session State": "-",
            "Availability": "-"
        })

# Export to Excel
output_file='f5_virtual_to_pool_summary.xlsx'
df = pd.DataFrame(all_data)
df.to_excel(output_file, index=False)
print(f"Excel file saved: {output_file}")


