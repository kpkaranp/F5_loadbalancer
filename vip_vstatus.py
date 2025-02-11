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
