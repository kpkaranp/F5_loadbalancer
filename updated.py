# Default to 'Unknown Enabled' if no proper status is found
status = "Unknown Enabled"

# Check if 'enabled' key exists
if 'enabled' in vip and vip['enabled']:
    # If 'status' field exists, determine if it's online or offline
    if 'status' in vip and 'availabilityState' in vip['status']:
        if vip['status']['availabilityState'] == "offline":
            status = "Offline Enabled"
        elif vip['status']['availabilityState'] == "online":
            status = "Online Enabled"
    else:
        status = "Unknown Enabled"  # If availabilityState is missing
