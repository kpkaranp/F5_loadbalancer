# API endpoint for VIP status
vip_status_url = f"{F5_HOST}/mgmt/tm/ltm/virtual"

vip_status_response = requests.get(vip_status_url, auth=auth, headers=headers, verify=False)

if vip_status_response.status_code == 200:
    vip_status_data = vip_status_response.json()
    vip_filename = f"vip_status_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    
    # Save VIP status data to a file
    with open(vip_filename, 'w') as f:
        json.dump(vip_status_data, f)
    print(f"VIP status saved: {vip_filename}")
else:
    print("Failed to fetch VIP status:", vip_status_response.text)