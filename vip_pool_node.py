import requests
import pandas as pd
from requests.auth import HTTPBasicAuth

# --- Configuration ---
f5_host = 'https://<F5-HOSTNAME_OR_IP>'  # e.g., 'https://192.168.1.245'
username = 'admin'
password = 'your_password'

# --- Setup ---
requests.packages.urllib3.disable_warnings()
auth = HTTPBasicAuth(username, password)
headers = {'Content-Type': 'application/json'}

def get_virtual_servers():
    url = f'{f5_host}/mgmt/tm/ltm/virtual'
    response = requests.get(url, auth=auth, headers=headers, verify=False)
    response.raise_for_status()
    return response.json().get('items', [])

def get_pool_members(pool_name):
    pool_path = f'~Common~{pool_name}'
    url = f'{f5_host}/mgmt/tm/ltm/pool/{pool_path}/members'
    response = requests.get(url, auth=auth, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json().get('items', [])
    return []

def main():
    data = []

    virtuals = get_virtual_servers()
    for vs in virtuals:
        vs_name = vs['name']
        pool_path = vs.get('pool')

        if pool_path:
            pool_name = pool_path.split('/')[-1]
            members = get_pool_members(pool_name)

            if members:
                for m in members:
                    data.append({
                        "Virtual Server": vs_name,
                        "Pool": pool_name,
                        "Pool Member (Node)": m['name']  # IP:Port
                    })
            else:
                data.append({
                    "Virtual Server": vs_name,
                    "Pool": pool_name,
                    "Pool Member (Node)": "No Members"
                })
        else:
            data.append({
                "Virtual Server": vs_name,
                "Pool": "No Pool",
                "Pool Member (Node)": "-"
            })

    # Create Excel file
    df = pd.DataFrame(data)
    df.to_excel("f5_virtual_server_mapping.xlsx", index=False)
    print("Exported to f5_virtual_server_mapping.xlsx")

if __name__ == '__main__':
    main()
