import requests

BIGIP_IP = "192.168.1.100"
AUTH_TOKEN = "YOUR_AUTH_TOKEN"

url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual"

headers = {
    "X-F5-Auth-Token": AUTH_TOKEN
}

response = requests.get(url, headers=headers, verify=False)

if response.status_code == 200:
    vips = response.json()["items"]
    for vip in vips:
        print(f"VIP Name: {vip['name']}")
        print(f"Destination: {vip['destination']}")
        print(f"Status: {vip['status']}")  # Status may be under 'state' or 'status'
        print("-" * 40)
else:
    print(f" Failed to get VIP status: {response.text}")


---------------------------------------------------------------------------------------

url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual/stats"

response = requests.get(url, headers=headers, verify=False)

if response.status_code == 200:
    stats = response.json()["entries"]
    for key, value in stats.items():
        vip_name = key.split("/")[-1]
        data = value["nestedStats"]["entries"]
        print(f"VIP: {vip_name}")
        print(f"  - Current Connections: {data['clientside.curConns']['value']}")
        print(f"  - Max Connections: {data['clientside.maxConns']['value']}")
        print(f"  - Total Bytes In: {data['clientside.bytesIn']['value']}")
        print(f"  - Total Bytes Out: {data['clientside.bytesOut']['value']}")
        print("-" * 40)
else:
    print(f"Failed to get traffic summary: {response.text}")

-----------------------------------------------------------------------

import requests
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # Disable SSL warnings

# Set F5 credentials
BIGIP_IP = os.getenv("F5_IP", "192.168.1.100")  # Replace with your F5 IP
AUTH_TOKEN = os.getenv("F5_TOKEN", "YOUR_AUTH_TOKEN")  # Replace with your F5 auth token

# API URL to fetch Virtual Servers
url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual?$filter=partition+ne+null"

# Headers with authentication token
headers = {
    "X-F5-Auth-Token": AUTH_TOKEN,
    "Content-Type": "application/json"
}

# Send API request
response = requests.get(url, headers=headers, verify=False)

# Check response
if response.status_code == 200:
    vips = response.json().get("items", [])
    print("Virtual Servers across all partitions:")
    for vip in vips:
        print(f"Partition: {vip['partition']} | VIP Name: {vip['name']} | Destination: {vip['destination']}")
else:
    print(f"Failed to fetch virtual servers: {response.text}")



---------------------------------------------------------------------------------------


import requests
import pandas as pd

# F5 Management IP and API token
f5_mgmt_ip = "<F5_MGMT_IP>"
token = "<YOUR_API_TOKEN>"

# API URL to get virtual servers (VIP details)
url = f"https://{f5_mgmt_ip}/mgmt/tm/ltm/virtual"

# Set the headers for authentication
headers = {
    'X-F5-Auth-Token': token
}

# Make the GET request
response = requests.get(url, headers=headers, verify=False)

# Check if the request was successful
if response.status_code == 200:
    vip_data = response.json()

    # List to hold processed data for Excel
    processed_data = []

    # Loop through the virtual servers and extract required details
    for vip in vip_data['items']:
        name = vip.get('name', 'N/A')
        full_partition = vip.get('partition', 'N/A')  # Full path partition
        destination = vip.get('destination', 'N/A')
        description = vip.get('description', 'N/A')
        status = 'enabled' if vip.get('enabled') else 'disabled'
        
        # Extract service port from the destination
        port = destination.split(":")[1] if ":" in destination else "N/A"

        # Add the processed data to the list
        processed_data.append({
            'Name': name,
            'Status': status,
            'Description': description,
            'Service Port': port,
            'Destination': destination,
            'Partition': full_partition
        })

    # Create a pandas DataFrame from the processed data
    df = pd.DataFrame(processed_data)

    # Export the DataFrame to an Excel file
    excel_file_path = "f5_vip_status.xlsx"
    df.to_excel(excel_file_path, index=False)

    print(f"Excel file has been created: {excel_file_path}")
else:
    print(f"Failed to retrieve data. Status code: {response.status_code}")


