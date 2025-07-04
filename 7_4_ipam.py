import os
from SOLIDserverRest import adv as sdsadv

# === Configuration ===
SDS_HOST = os.environ['SDS_HOST_DEV']
SDS_LOGIN = os.environ['SDS_LOGIN_DEV']
SDS_PWD = os.environ['SDS_PWD_DEV']

TARGET_IP = "100.30.1.25"  # Make sure it's a valid IPv4 address

# === Connect to SOLIDserver ===
sds = sdsadv.SDS(ip_address=SDS_HOST, user=SDS_LOGIN, pwd=SDS_PWD)

try:
    sds.connect()
    print("Connected to SOLIDserver.")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

# === Get info for a specific IP ===
try:
    ip_detail = sds.ip_address_info({
        "ip_addr": TARGET_IP
    })

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
        print(f"No details found for IP: {TARGET_IP}")

except Exception as e:
    print(f" Failed to get IP info: {e}")
