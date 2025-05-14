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


def connectToF5(url, auth_token, debug=True, return_encoding='json'):
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

class F5Config:
    def __init__(self, bigip_address, username, password, debug=False):
        self.token = f5_auth_token(bigip_address, username, password, uri='/mgmt/shared/authn/login')
        self.debug = debug
        self.address= bigip_address
        self.username= username
        self.password= password
        vip_status(self)

# This function assumes it is a method of a class with self.address and self.token
# It uses only the 'name' (not full path) for all mapping and output


BIGIP_IP = self.address
AUTH_TOKEN = self.token

headers = {
    "X-F5-Auth-Token": AUTH_TOKEN,
    "Content-Type": "application/json"
}

def get_virtuals():
    url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual"
    r = requests.get(url, headers=headers, verify=False)
    r.raise_for_status()
    return r.json().get('items', [])

def get_virtual_stats():
    url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual/stats"
    r = requests.get(url, headers=headers, verify=False)
    r.raise_for_status()
    return r.json().get('entries', {})

def get_pools():
    url = f"https://{BIGIP_IP}/mgmt/tm/ltm/pool"
    r = requests.get(url, headers=headers, verify=False)
    r.raise_for_status()
    return r.json().get('items', [])

def get_pool_stats():
    url = f"https://{BIGIP_IP}/mgmt/tm/ltm/pool/stats"
    r = requests.get(url, headers=headers, verify=False)
    r.raise_for_status()
    return r.json().get('entries', {})

def get_pool_members(pool_full_path):
    pool_uri = pool_full_path.replace('/', '~')
    url = f"https://{BIGIP_IP}/mgmt/tm/ltm/pool/{pool_uri}/members"
    r = requests.get(url, headers=headers, verify=False)
    if r.status_code == 200:
        return r.json().get('items', [])
    return []

virtuals = get_virtuals()
stats = get_virtual_stats()
pools = get_pools()
pool_stats = get_pool_stats()

# Build VS info map by name only
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

# Build pool info map by name only
pool_info_map = {}
for stat in pool_stats.values():
    nested = stat.get('nestedStats', {}).get('entries', {})
    name = nested.get('tmName', {}).get('description', '')
    status = nested.get('status.availabilityState', {}).get('description', '')
    status_desc = nested.get('status.statusReason', {}).get('description', '')
    active_members = nested.get('activeMemberCount', {}).get('value', 0)
    total_members = nested.get('memberCount', {}).get('value', 0)
    pool_info_map[name] = {
        'status': status,
        'status_desc': status_desc,
        'active_members': active_members,
        'total_members': total_members
    }

# Map VS name to pool and description
vs_pool_map = {}
vs_desc_map = {}
for vs in virtuals:
    vs_name = vs['name']
    pool = vs.get('pool', None)
    if pool:
        if pool.startswith('/'):
            pool_name = pool.split('/')[-1]
        else:
            pool_name = pool
        vs_pool_map[vs_name] = pool_name
    desc = vs.get('description', '')
    vs_desc_map[vs_name] = desc

# Collect all data
all_rows = []
for pool in pools:
    pool_name = pool['name']
    members = get_pool_members(pool['fullPath'])
    pool_info = pool_info_map.get(pool_name, {})
    # Find which VSs use this pool
    linked_vs_names = [k for k, v in vs_pool_map.items() if v == pool_name]
    if not linked_vs_names:
        linked_vs_names = ['Unlinked']
    for vs_name in linked_vs_names:
        vs_info = vs_info_map.get(vs_name, {})
        row_base = {
            'Virtual Server': vs_name,
            'VS Description': vs_desc_map.get(vs_name, ''),
            'Destination': vs_info.get('destination', ''),
            'Service Port': vs_info.get('port', ''),
            'VS Status': vs_info.get('status', ''),
            'VS Status Reason': vs_info.get('status_desc', ''),
            'Pool': pool_name,
            'Pool Status': pool_info.get('status', ''),
            'Pool Status Reason': pool_info.get('status_desc', ''),
            'Active Members': pool_info.get('active_members', 0),
            'Total Members': pool_info.get('total_members', 0)
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
# Save to Excel
df = pd.DataFrame(all_rows)
timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
filename = f"{BIGIP_IP}_f5_summary_{timestamp}_vsnameonly.xlsx"
df.to_excel(filename, index=False)
print(f"Excel file saved: {filename}") 
