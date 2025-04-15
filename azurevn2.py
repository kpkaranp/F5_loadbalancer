import subprocess
import json
from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
import pandas as pd
import re

def get_all_subscriptions():
    result = subprocess.check_output(["az", "account", "list", "--output", "json"])
    subs = json.loads(result)
    return [sub["id"] for sub in subs if sub["state"] == "Enabled"]

def extract_resource_group(resource_id):
    match = re.search(r"/resourceGroups/([^/]+)/", resource_id, re.IGNORECASE)
    return match.group(1) if match else None

def main():
    credential = DefaultAzureCredential()
    all_data = []

    subscriptions = get_all_subscriptions()
    print("Found {len(subscriptions)} subscriptions.")

    for sub_id in subscriptions:
        print("Working on subscription: {sub_id}")
        network_client = NetworkManagementClient(credential, sub_id)

        try:
            vnets = list(network_client.virtual_networks.list_all())
        except Exception as e:
            print(" Could not fetch VNets for subscription {sub_id}: {e}")
            continue

        for vnet in vnets:
            if "hub" in vnet.name.lower():
                vnet_name = vnet.name
                vnet_rg = extract_resource_group(vnet.id)
                print("Found HUB VNet: {vnet_name} in {vnet_rg}")

                try:
                    peerings = list(network_client.virtual_network_peerings.list(vnet_rg, vnet_name))
                except Exception as e:
                    print("Error fetching peerings for {vnet_name}: {e}")
                    continue

                for peer in peerings:
                    all_data.append({
                        "Subscription ID": sub_id,
                        "VNet Name": vnet_name,
                        "VNet Resource Group": vnet_rg,
                        "VNet Location": vnet.location,
                        "Peering Name": peer.name,
                        "Peering State": peer.peering_state,
                        "Peer VNet ID": peer.remote_virtual_network.id,
                        "Allow VNet Access": peer.allow_virtual_network_access,
                        "Allow Forwarded Traffic": peer.allow_forwarded_traffic,
                        "Allow Gateway Transit": peer.allow_gateway_transit
                    })

    # Save to Excel
    if all_data:
        df = pd.DataFrame(all_data)
        df.to_excel("hub_vnet_peerings.xlsx", index=False)
        print("Exported peerings to hub_vnet_peerings.xlsx")
    else:
        print("No HUB VNets with peerings found.")

if __name__ == "__main__":
    main()
