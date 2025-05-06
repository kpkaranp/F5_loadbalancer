#!/usr/bin/env python

from base64 import b64encode
import json
import os
import sys
import time
import requests
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
import pprint
import pandas as pd


class F5Config:
    
    def __init__(self, bigip_address, username, password, debug=False):
        
        self.token = f5_auth_token(bigip_address, username, password, uri='/mgmt/shared/authn/login')
        self.debug = debug
        self.address= bigip_address
        self.username= username
        self.password= password
        

        vip_status(self)


def f5_auth_token(address, user, password,
                   uri='/mgmt/shared/authn/login'):  # -> unicode
    """Get and auth token( to be used but other requests"""
    credentials_list = [user, ":", password]
    credentials = ''.join(credentials_list)
    user_and_pass = b64encode(credentials.encode()).decode("ascii")
    headers = { 'Authorization':'Basic {}'.format(user_and_pass), 'Content-Type':'application/json'}
    post_data = '{"username":"' + user + '","password":"' + password +'"}'
    url_list = ['https://', address, uri]
    url = ''.join(url_list)
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    try:
        request_result = requests.post(url, headers=headers, data=post_data, verify=False)
    except requests.exceptions.ConnectionError as connection_error:
        print(connection_error)
        sys.exit(connection_error)
    except requests.exceptions.RequestException as request_exception:
        print(request_exception)
        sys.exit(request_exception)
    print (request_result.json())
    if "token" not in request_result.json().keys(): 
      #print ("issue in generating token")
       sys.exit("issue in generating token")   
    #returns an instance of unicode that is an auth token with 300 dec timeout
    return request_result.json()['token']['token']


def  connectToF5(url, auth_token, debug=True, return_encoding='json'):
    """Generic GET function. The return_encoding can be:'text', 'json', 'content'(binary),
    or raw """
    headers = {'X-F5-Auth-Token':'{}'.format(auth_token), 'Content-Type':'application/json'}

    get_result = requests.get(url, headers=headers, verify=False)

    if isinstance(get_result.json(), dict):
        if "items" in get_result.json().keys():
            if get_result.json()["items"] :
                return get_result.json()["items"]
    #print(f"issue getting information from : {url}")
    return None

def vip_status(self):
    BIGIP_IP = self.address
    AUTH_TOKEN = self.token
   
# Headers with authentication token
    headers = {
    "X-F5-Auth-Token": AUTH_TOKEN,
    "Content-Type": "application/json"
    }

  # --- Fetch virtual server list ---
    def get_virtuals():
        url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual"
        r = requests.get(url, headers=headers, verify=False)
        r.raise_for_status()
        return r.json().get('items', [])
  
  # --- Fetch virtual server stats ---
    def get_virtual_stats():
        url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual/stats"
        r = requests.get(url, headers=headers, verify=False)
        r.raise_for_status()
        return r.json().get('entries', {})
  
  # --- Fetch all pools ---
    def get_pools():
        url = f"https://{BIGIP_IP}/mgmt/tm/ltm/pool"
        r = requests.get(url, headers=headers, verify=False)
        r.raise_for_status()
        return r.json().get('items', [])
  
  # --- Fetch pool members ---
    def get_pool_members(pool_full_path):
        pool_uri = pool_full_path.replace('/', '~')
        url = f"https://{BIGIP_IP}/mgmt/tm/ltm/pool/{pool_uri}/members"
        r = requests.get(url, auth=auth, headers=headers, verify=False)
        if r.status_code == 200:
            return r.json().get('items', [])
        return []

# --- Main Processing ---
def generate_summary_excel():
    virtuals = get_virtuals()
    stats = get_virtual_stats()
    pools = get_pools()

    # --- Build virtual server info map (name → details) ---
    vs_info_map = {}
    for stat in stats.values():
        nested = stat.get('nestedStats', {}).get('entries', {})
        name = nested.get('tmName', {}).get('description', '')
        dest = nested.get('destination', {}).get('description', '')
        status = nested.get('status.availabilityState', {}).get('description', '')
        status_desc = nested.get('status.statusReason', {}).get('description', '')
        port = dest.split(':')[-1] if ':' in dest else 'N/A'
        vs_info_map[name] = {
            'destination': dest,
            'port': port,
            'status': status,
            'status_desc': status_desc
        }

    # Map virtual server name to its pool and description
    vs_pool_map = {}
    vs_desc_map = {}
    for vs in virtuals:
        full_name = vs['fullPath']  # e.g., /Common/vs_web
        vs_name = vs['name']
        pool = vs.get('pool', None)  # e.g., /Common/pool_web
        desc = vs.get('description', '')
        if pool:
            pool_uri = pool.strip('/').replace('/', '~')
            vs_pool_map[vs_name] = pool
        vs_desc_map[vs_name] = desc

    # --- Collect all data ---
    all_rows = []
    for pool in pools:
        pool_path = pool['fullPath']
        pool_uri = pool_path.replace('/', '~')
        members = get_pool_members(pool_path)

        # Find which VSs use this pool
        linked_vs_names = [k for k, v in vs_pool_map.items() if v == pool_path]
        if not linked_vs_names:
            linked_vs_names = ['Unlinked']

        for vs_name in linked_vs_names:
            vs_info = vs_info_map.get(f"/Common/{vs_name}", {})
            row_base = {
                'Virtual Server': vs_name,
                'VS Description': vs_desc_map.get(vs_name, ''),
                'Destination': vs_info.get('destination', ''),
                'Service Port': vs_info.get('port', ''),
                'VS Status': vs_info.get('status', ''),
                'VS Status Reason': vs_info.get('status_desc', ''),
                'Pool': pool_path
            }

            if members:
                for member in members:
                    all_rows.append({
                        **row_base,
                        'Pool Member': member.get('name'),
                        'Node IP': member.get('address', 'N/A'),
                        'Member Status': member.get('state', 'unknown'),
                        'Session': member.get('session', 'unknown')
                    })
            else:
                all_rows.append({
                    **row_base,
                    'Pool Member': 'No Members',
                    'Node IP': '-',
                    'Member Status': '-',
                    'Session': '-'
                })

    # --- Save to Excel ---
    df = pd.DataFrame(all_rows)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{BIGIP_IP}_f5_summary_{timestamp}.xlsx"
    df.to_excel(filename, index=False)
    print(f"Excel file saved: {filename}")
generate_summary_excel()
