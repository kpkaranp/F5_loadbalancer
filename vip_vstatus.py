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

