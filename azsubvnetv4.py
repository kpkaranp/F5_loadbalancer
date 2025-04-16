import subprocess
import json
import re
import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient

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
    print(f"Found {len(subscriptions)} subscriptions.")

    for sub_id in subscriptions:
        print("Working on subscription: {sub_id}")
        network_client = NetworkManagementClient(credential, sub_id)

        try:
            vnets = list(network_client.virtual_networks.list_all())
        except Exception as e:
            print("Could not fetch VNets for subscription {sub_id}: {e}")
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
                    peer_vnet_id = peer.remote_virtual_network.id

                    # Extract peer subscription, resource group, and VNet name
                    try:
                        peer_subscription_id = re.search(r"/subscriptions/([^/]+)", peer_vnet_id, re.IGNORECASE).group(1)
                        peer_resource_group = re.search(r"/resourceGroups/([^/]+)", peer_vnet_id, re.IGNORECASE).group(1)
                        peer_vnet_name = peer_vnet_id.split("/virtualNetworks/")[1]
                    except Exception as e:
                        print("Error parsing peer VNet ID {peer_vnet_id}: {e}")
                        peer_subscription_id = peer_resource_group = peer_vnet_name = "Unavailable"

                    # Try to get the peered VNet's address space from the correct subscription
                    try:
                        peer_client = NetworkManagementClient(credential, peer_subscription_id)
                        remote_vnet = peer_client.virtual_networks.get(peer_resource_group, peer_vnet_name)
                        address_ranges = remote_vnet.address_space.address_prefixes
                    except Exception as e:
                        print("Error fetching address space for {peer_vnet_name} (sub {peer_subscription_id}): {e}")
                        address_ranges = ["Unavailable"]

                    for cidr in address_ranges:
                        all_data.append({
                            "Hub Subscription ID": sub_id,
                            "Hub VNet Name": vnet_name,
                            "Hub VNet Resource Group": vnet_rg,
                            "Hub VNet Location": vnet.location,
                            "Peering Name": peer.name,
                            "Peering State": peer.peering_state,
                            "Spoke Peer Subscription": peer_subscription_id,
                            "Spoke Peer Resource Group": peer_resource_group,
                            "Spoke Peer Name": peer_vnet_name,
                            "Allow VNet Access": peer.allow_virtual_network_access,
                            "Allow Forwarded Traffic": peer.allow_forwarded_traffic,
                            "Allow Gateway Transit": peer.allow_gateway_transit,
                            "Peering IP Address Range": cidr
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
