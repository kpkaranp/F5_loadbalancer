from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
import pandas as pd

# Replace with your Subscription ID
subscription_id = "YOUR_SUBSCRIPTION_ID"

# Authenticate
credential = DefaultAzureCredential()
network_client = NetworkManagementClient(credential, subscription_id)

# Collect data
data = []

# List all virtual networks
for vnet in network_client.virtual_networks.list_all():
    vnet_name = vnet.name
    vnet_rg = vnet.id.split('/')[4]
    vnet_location = vnet.location

    # Get peerings for the VNet
    peerings = network_client.virtual_network_peerings.list(vnet_rg, vnet_name)

    for peer in peerings:
        data.append({
            "VNet Name": vnet_name,
            "VNet Resource Group": vnet_rg,
            "VNet Location": vnet_location,
            "Peering Name": peer.name,
            "Peer VNet ID": peer.remote_virtual_network.id,
            "Peering State": peer.peering_state,
            "Allow Virtual Network Access": peer.allow_virtual_network_access,
            "Allow Forwarded Traffic": peer.allow_forwarded_traffic,
            "Allow Gateway Transit": peer.allow_gateway_transit
        })

# Export to Excel
df = pd.DataFrame(data)
df.to_excel("azure_vnet_peerings.xlsx", index=False)

print("Exported to azure_vnet_peerings.xlsx")
