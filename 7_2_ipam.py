from SOLIDserverRest import adv as sdsadv

# === Configuration ===
SDS_HOST = "https://your-sds-server"  # Replace with your SOLIDserver IP or hostname
SDS_LOGIN = "your_username"           # Replace with your username
SDS_PWD = "your_password"             # Replace with your password
TARGET_IP = "192.0.2.5"               # Replace with the IP you want to get details for

# === Connect to SOLIDserver ===
sds = sdsadv.SDS(ip_address=SDS_HOST, user=SDS_LOGIN, pwd=SDS_PWD)

try:
    sds.connect()
    print("Connected to SOLIDserver successfully.")
except Exception as e:
    print(f"Connection failed: {e}")
    exit()

# === Get Detailed Info for a Specific IP Address ===
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
        print(f"No details found for IP address: {TARGET_IP}")

except Exception as e:
    print(f"Failed to retrieve IP address info: {e}")
