#!/usr/bin/env python

from base64 import b64encode
import json
import os
import sys
import time
import requests
from urllib3.exceptions import InsecureRequestWarning
import pandas as pd

class F5Config:
    def _init_(self, bigip_address, username, password, debug=False):
        self.token = f5_auth_token(bigip_address, username, password, uri='/mgmt/shared/authn/login')
        self.debug = debug
        self.address = bigip_address
        self.username = username
        self.password = password

        vip_status(self)

def f5_auth_token(address, user, password, uri='/mgmt/shared/authn/login'):
    """Get an authentication token from the F5 device."""
    credentials = f"{user}:{password}"
    user_and_pass = b64encode(credentials.encode()).decode("ascii")
    headers = {'Authorization': f'Basic {user_and_pass}', 'Content-Type': 'application/json'}
    post_data = json.dumps({"username": user, "password": password})
    url = f"https://{address}{uri}"

    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    try:
        request_result = requests.post(url, headers=headers, data=post_data, verify=False)
        request_result.raise_for_status()
    except requests.exceptions.RequestException as err:
        print(f"Error: {err}")
        sys.exit(err)

    response_data = request_result.json()
    if "token" not in response_data:
        sys.exit("Issue in generating token")

    return response_data['token']['token']

def vip_status(self):
    """Fetch and save VIP details including status."""
    BIGIP_IP = self.address
    AUTH_TOKEN = self.token

    headers = {
        "X-F5-Auth-Token": AUTH_TOKEN,
        "Content-Type": "application/json"
    }

    url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual"

    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print(f"Failed to retrieve data: {err}")
        return

    vip_data = response.json()

    processed_data = []

    for vip in vip_data.get('items', []):
        name = vip.get('name', 'N/A')
        full_partition = vip.get('partition', 'N/A')
        destination = vip.get('destination', 'N/A')
        description = vip.get('description', 'N/A')

        # Extract service port from the destination
        port = destination.split(":")[1] if ":" in destination else "N/A"

        # Determine the status based on availability
        status = "Unknown Enabled"
        if vip.get('enabled', False):
            if 'status' in vip and 'availabilityState' in vip['status']:
                if vip['status']['availabilityState'] == "offline":
                    status = "Offline Enabled"
                elif vip['status']['availabilityState'] == "online":
                    status = "Online Enabled"

        processed_data.append({
            'Name': name,
            'Status': status,
            'Description': description,
            'Service Port': port,
            'Destination': destination,
            'Partition': full_partition
        })

    df = pd.DataFrame(processed_data)
    excel_file_path = "f5_vip_status.xlsx"
    df.to_excel(excel_file_path, index=False)

    print(f"Excel file has been created: {excel_file_path}")
