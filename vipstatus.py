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

# The URLs to fetch data from the F5 API
    status_url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual/stats"
    virtual_url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual"
    
    # Disable SSL verification (Optional, only if you have an SSL certificate issue)
    # You can remove verify=False if you're using a valid SSL cert
    response_status = requests.get(status_url, headers=headers, verify=False)
    response_virtual = requests.get(virtual_url, headers=headers, verify=False)
    
    # Check if both requests were successful
    if response_status.status_code == 200 and response_virtual.status_code == 200:
        # Parse the JSON responses
        status_data = response_status.json()
        virtual_data = response_virtual.json()
    
        # Prepare a list to store extracted information
        extracted_data = []
    
        # Loop through each virtual server entry in the status data
        for vip in status_data.get('entries', {}).values():
            nested_stats = vip.get('nestedStats', {}).get('entries', {})
    
            # Extract values from status data
            name = nested_stats.get('tmName', {}).get('description', 'N/A')
            destination = nested_stats.get('destination', {}).get('description', 'N/A')
            description = nested_stats.get('status.statusReason', {}).get('description', 'N/A')
            status = nested_stats.get('status.availabilityState', {}).get('description', 'N/A')
            full_partition = name.split('/')[1] if '/' in name else "N/A"
            port = destination.split(":")[1] if ":" in destination else "N/A"
    
    
            # Trim the partition from the status name to match the virtual name
            virtual_name = name.split('/')[-1]  # Get the part after the last '/'
            
            
            virtual_info = next((v for v in virtual_data.get('items', []) if v.get('name') == virtual_name), None)
            print(virtual_info,"vinfo")
            vdescription = virtual_info.get('description', 'N/A') if virtual_info else 'N/A'
            print(vdescription)
           
            
        # Add to the list of extracted data
            extracted_data.append({
                'Name': name,
                'Status': status,
                'Status Description': description,
                'Destination': destination,
                'Partition': full_partition,
                'Description': vdescription,
                'Service Port': port
            })

        # Convert the list to a pandas DataFrame
        df = pd.DataFrame(extracted_data)
    
        # Get current date and time for the file name
        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{BIGIP_IP}_{current_datetime}.xlsx"
    
        # Save to Excel
        df.to_excel(file_name, index=False)
    
        print(f"Data saved successfully to {file_name}")
    
    else:
        print(f"Failed to fetch data. Status code for status: {response_status.status_code}, virtual: {response_virtual.status_code}")
      
               
           
