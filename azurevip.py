import subprocess
import json
from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
import pandas as pd

# Step 1: Get the default subscription ID using Azure CLI
def get_subscription_id():
    try:
        account_info = subprocess.check_output(["az", "account", "show", "--output", "json"])
        subscription_id = json.loads(account_info)["id"]
        return subscription_id
    except Exception as e:
        print(" Error fetching subscription ID. Make sure you're logged in using `az login`.")
        raise e

# Step 2: Authenticate and create network client
subscription_id = get_subscription_id()
credential = DefaultAzureCredential()
network_client = NetworkManagementClient(credential, subscription_id)

# Step 3: Collect VNet and peering info
data = []

print("Fetching virtual networks and peerings...")

for vnet in network_client.virtual_networks.list_all():
    vnet_name = vnet.name
    vnet_rg = vnet.id.split('/')[4]
    vnet_location = vnet.location

    peerings = network_client.virtual_network_peerings.list(vnet_rg, vnet_name)

    for peer in peerings:
        data.append({
            "VNet Name": vnet_name,
            "VNet Resource Group": vnet_rg,
            "VNet Location": vnet_location,
            "Peering Name": peer.name,
            "Peering State": peer.peering_state,
            "Peer VNet ID": peer.remote_virtual_network.id,
            "Allow VNet Access": peer.allow_virtual_network_access,
            "Allow Forwarded Traffic": peer.allow_forwarded_traffic,
            "Allow Gateway Transit": peer.allow_gateway_transit
        })

# Step 4: Export to Excel
df = pd.DataFrame(data)
output_file = "azure_vnet_peerings.xlsx"
df.to_excel(output_file, index=False)

print(f" Exported to {output_file}")
