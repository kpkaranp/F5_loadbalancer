# API endpoint for QKView
qkview_url = f"{F5_HOST}/mgmt/tm/sys/diagnostic/qkview"

# Filename for QKView backup
qkview_filename = f"qkview_{datetime.now().strftime('%Y%m%d%H%M%S')}.tgz"

qkview_response = requests.post(qkview_url, auth=auth, headers=headers, json={}, verify=False)

if qkview_response.status_code == 200:
    print(f"QKView backup created: {qkview_filename}")
else:
    print("QKView backup failed:", qkview_response.text)