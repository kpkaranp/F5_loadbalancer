import requests
import os
from datetime import datetime

# F5 Device Credentials
F5_HOST = "https://<F5_MGMT_IP>"
USERNAME = "admin"
PASSWORD = "your_password"

# API endpoint for UCS backup
url = f"{F5_HOST}/mgmt/tm/sys/ucs"

headers = {
    "Content-Type": "application/json"
}

auth = (USERNAME, PASSWORD)

# Filename for UCS backup
backup_filename = f"backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.ucs"
data = {
    "command": "save",
    "name": backup_filename
}

response = requests.post(url, auth=auth, headers=headers, json=data, verify=False)

if response.status_code == 200:
    print(f"UCS backup created: {backup_filename}")
else:
    print("UCS backup failed:", response.text)