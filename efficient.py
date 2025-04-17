from SOLIDserverRest import adv as sdsadv

# === Configuration ===
SDS_HOST = "https://your-sds-server"  # Replace with your SOLIDserver IP or hostname
SDS_LOGIN = "your_username"           # Replace with your username
SDS_PWD = "your_password"             # Replace with your password
SPACE_NAME = "your_ip_space_name"     # Replace with your IP space (IP class) name

# === Connect to SOLIDserver ===
sds = sdsadv.SDS(ip_address=SDS_HOST, user=SDS_LOGIN, pwd=SDS_PWD)

try:
    sds.connect()
    print("Connected to SOLIDserver successfully.")
except Exception as e:
    print(f"Connection failed: {e}")
    exit()

# === Retrieve All IPv4 Addresses in a Space ===
try:
    ip_list = sds.ip_address_list({
        "WHERE": f"site_name='{SPACE_NAME}'"
    })

    if ip_list:
        print(f"\nFound {len(ip_list)} IP addresses in '{SPACE_NAME}':\n")
        for ip in ip_list:
            print(f"IP Address : {ip.get('ip_addr')}")
            print(f"Status     : {ip.get('ip_status')}")
            print(f"MAC Addr   : {ip.get('ip_mac_addr')}")
            print(f"Host Name  : {ip.get('ip_hostdev_name')}")
            print(f"Class Name : {ip.get('ip_class_name')}")
            print(f"Description: {ip.get('ip_description')}")
            print("-" * 40)
    else:
        print("No IP addresses found in the given space.")

except Exception as e:
    print(f"Failed to retrieve IP addresses: {e}")
