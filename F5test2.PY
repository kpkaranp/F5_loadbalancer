import requests
import time

# Replace with your F5 BIG-IP details
BIGIP_IP = "192.168.1.100"
AUTH_TOKEN = "YOUR_AUTH_TOKEN"
QKVIEW_FILE = "/var/tmp/my_qkview.qkview"
LOCAL_FILE = "my_qkview.qkview"

headers = {
    "X-F5-Auth-Token": AUTH_TOKEN,
    "Content-Type": "application/json"
}

# Step 1: Generate QKView
def generate_qkview():
    url = f"https://{BIGIP_IP}/mgmt/tm/util/qkview"
    data = {
        "command": "run",
        "utilCmdArgs": f"-f {QKVIEW_FILE}"
    }

    response = requests.post(url, headers=headers, json=data, verify=False)

    if response.status_code == 200:
        print("✅ QKView generation started successfully!")
    else:
        print(f"❌ Failed to start QKView generation: {response.text}")
        exit(1)  # Stop execution if failed
```
