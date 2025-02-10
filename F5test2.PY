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

# Step 2: Check if QKView is ready every 2 minutes
def check_qkview_status():
    status_url = f"https://{BIGIP_IP}/mgmt/tm/util/bash"
    status_data = {
        "command": "run",
        "utilCmdArgs": f"-c 'ls -l {QKVIEW_FILE}'"
    }

    print("⏳ Waiting for QKView to be generated (checking every 2 minutes)...")

    while True:
        response = requests.post(status_url, headers=headers, json=status_data, verify=False)
        
        if QKVIEW_FILE in response.text:
            print("✅ QKView file is ready for download.")
            break
        else:
            print("⏳ QKView not ready yet. Checking again in 2 minutes...")
            time.sleep(120)  # Wait for 2 minutes before checking again

# Step 3: Download QKView
def download_qkview():
    download_url = f"https://{BIGIP_IP}/mgmt/shared/file-transfer/downloads/my_qkview.qkview"

    print("⬇️  Downloading QKView file...")

    response = requests.get(download_url, headers=headers, verify=False)

    if response.status_code == 200:
        with open(LOCAL_FILE, "wb") as f:
            f.write(response.content)
        print(f"✅ QKView file downloaded successfully! Saved as {LOCAL_FILE}")
    else:
        print(f"❌ Failed to download QKView: {response.text}")

# Run the full workflow
generate_qkview()
check_qkview_status()
download_qkview()
