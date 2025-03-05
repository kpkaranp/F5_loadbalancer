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

    # The URL to fetch data from the F5 API
    url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual"
    #status_url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual/status"

    # Make the GET request
    response = requests.get(url, headers=headers, verify=False)
    #status_response = requests.get(url, headers=headers, verify=False)
    #print(status_response)
    
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
               
           
