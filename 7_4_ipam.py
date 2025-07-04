import os
import json
import sys
import logging
import ipam 


SDS_HOST_DEV = os.environ['SDS_HOST_DEV']
SDS_LOGIN_DEV = os.environ['SDS_LOGIN_DEV']
SDS_PWD_DEV = os.environ['SDS_PWD_DEV']
TARGET_IP = "100.302.1.25"  # Replace with the IP you want to look up

 
eip = ipam.Ipam(SDS_HOST_DEV, SDS_LOGIN_DEV, SDS_PWD_DEV)

try:
    ip_detail = eip.get_ip_details(TARGET_IP)  # Replace with your actual method if different

    if ip_detail:
        print(f"\nDetails for IP {TARGET_IP}:\n")
        print(f"IP Address : {ip_detail.get('ip_addr')}")
        print(f"Status     : {ip_detail.get('ip_status')}")
        print(f"MAC Addr   : {ip_detail.get('ip_mac_addr')}")
        print(f"Host Name  : {ip_detail.get('ip_hostdev_name')}")
        print(f"Class Name : {ip_detail.get('ip_class_name')}")
        print(f"Description: {ip_detail.get('ip_description')}")
        print(f"Site Name  : {ip_detail.get('site_name')}")
        print("-" * 40)
    else:
        print(f"No details found for IP address: {TARGET_IP}")

except Exception as e:
    print(f"Failed to retrieve IP address info: {e}")
