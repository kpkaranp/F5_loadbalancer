import pandas as pd
import requests
import argparse
import sys
import os
import json
from urllib3.exceptions import InsecureRequestWarning
import warnings
import base64
from datetime import datetime

# Suppress only the single warning from urllib3 needed.
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

def get_credentials():
    """
    Get F5 credentials from environment variables (GitHub secrets).
    """
    username = os.getenv('API_USERNAME')
    password = os.getenv('API_PASSWORD')
    
    if not username or not password:
        print("Error: API_USERNAME and API_PASSWORD environment variables must be set")
        print("Please ensure these GitHub secrets are properly configured")
        sys.exit(1)
    
    return username, password

def load_inventory(inventory_file):
    """
    Load device inventory from JSON file.
    """
    try:
        with open(inventory_file, 'r') as f:
            inventory = json.load(f)
            # The inventory is already an array of device objects
            return inventory
    except FileNotFoundError:
        print(f"Error: Inventory file {inventory_file} not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {inventory_file}")
        sys.exit(1)

def get_auth_token(address, username, password):
    """
    Get authentication token from F5 device using username and password.
    """
    auth_url = f"https://{address}/mgmt/shared/authn/login"
    auth_data = {
        "username": username,
        "password": password,
        "loginProviderName": "tmos"
    }
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(auth_url, json=auth_data, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()['token']['token']
    except requests.exceptions.RequestException as e:
        print(f"Authentication failed for {address}: {e}")
        return None

def fetch_f5_summary(address):
    """
    Fetches F5 summary stats using credentials from environment variables.
    """
    def get_stats(url, token):
        headers = {'X-F5-Auth-Token': token, 'Content-Type': 'application/json'}
        r = requests.get(url, headers=headers, verify=False)
        r.raise_for_status()
        return r.json()

    def parse_stats_entries(stats_json):
        entries = stats_json.get('entries', {})
        total = len(entries)
        available = unavailable = offline = unknown = 0
        available_disabled = offline_disabled = unknown_disabled = 0
        for entry in entries.values():
            nested = entry.get('nestedStats', {}).get('entries', {})
            status = nested.get('status.availabilityState', {}).get('description', '').lower()
            enabled = nested.get('status.enabledState', {}).get('description', '').lower()
            disabled = enabled == 'disabled'
            if status == 'available':
                available += 1
                if disabled:
                    available_disabled += 1
            elif status == 'unavailable':
                unavailable += 1
            elif status == 'offline':
                offline += 1
                if disabled:
                    offline_disabled += 1
            elif status == 'unknown':
                unknown += 1
                if disabled:
                    unknown_disabled += 1
        return total, available, available_disabled, unavailable, offline, offline_disabled, unknown, unknown_disabled

    try:
        # Get credentials from environment variables
        username, password = get_credentials()
        
        # Get authentication token
        token = get_auth_token(address, username, password)
        if not token:
            return None
        
        # Virtual Servers
        vs_url = f"https://{address}/mgmt/tm/ltm/virtual/stats"
        vs_stats_json = get_stats(vs_url, token)
        vs_total, vs_avail, vs_avail_dis, vs_unavail, vs_off, vs_off_dis, vs_unk, vs_unk_dis = parse_stats_entries(vs_stats_json)

        # Pools
        pool_url = f"https://{address}/mgmt/tm/ltm/pool/stats"
        pool_stats_json = get_stats(pool_url, token)
        pool_total, pool_avail, pool_avail_dis, pool_unavail, pool_off, pool_off_dis, pool_unk, pool_unk_dis = parse_stats_entries(pool_stats_json)

        # Nodes
        node_url = f"https://{address}/mgmt/tm/ltm/node/stats"
        node_stats_json = get_stats(node_url, token)
        node_total, node_avail, node_avail_dis, node_unavail, node_off, node_off_dis, node_unk, node_unk_dis = parse_stats_entries(node_stats_json)

        # Build summary DataFrame
        summary_df = pd.DataFrame([
            {
                "Object Type": "Virtual Servers",
                "Total": vs_total,
                "Available": f"{vs_avail} ({vs_avail_dis} Disabled)",
                "Unavailable": vs_unavail,
                "Offline": f"{vs_off} ({vs_off_dis} Disabled)",
                "Unknown": f"{vs_unk} ({vs_unk_dis} Disabled)"
            },
            {
                "Object Type": "Pools",
                "Total": pool_total,
                "Available": f"{pool_avail} ({pool_avail_dis} Disabled)",
                "Unavailable": pool_unavail,
                "Offline": f"{pool_off} ({pool_off_dis} Disabled)",
                "Unknown": f"{pool_unk} ({pool_unk_dis} Disabled)"
            },
            {
                "Object Type": "Nodes",
                "Total": node_total,
                "Available": f"{node_avail} ({node_avail_dis} Disabled)",
                "Unavailable": node_unavail,
                "Offline": f"{node_off} ({node_off_dis} Disabled)",
                "Unknown": f"{node_unk} ({node_unk_dis} Disabled)"
            }
        ])
        return summary_df
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from F5 device {address}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error for device {address}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Fetch F5 device status summary and save to CSV')
    parser.add_argument('--inventory', '-i', default='inventory.json',
                      help='Path to inventory JSON file (default: inventory.json)')
    parser.add_argument('--output', '-o', default='f5_status_summary',
                      help='Output CSV file base name (default: f5_status_summary)')
    
    args = parser.parse_args()
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"{args.output}_{timestamp}.csv"
    
    # Load device inventory using default inventory.json in the same directory
    devices = load_inventory('inventory.json')
    
    # Process each device
    all_summaries = []
    for device_info in devices:
        dc = device_info.get('dc', 'Unknown')
        device = device_info.get('device')
        
        print(f"\nProcessing device: {device}")
        print(f"Datacenter: {dc}")
        
        summary_df = fetch_f5_summary(device)
        
        if summary_df is not None:
            # Add only dc and device information columns
            summary_df['Datacenter'] = dc
            summary_df['Device'] = device
            
            # Add to combined summary
            all_summaries.append(summary_df)
    
    # Save combined summary if we have any successful results
    if all_summaries:
        combined_df = pd.concat(all_summaries, ignore_index=True)
        # Reorder columns to put device information first and Total last
        device_cols = ['Datacenter', 'Device']
        other_cols = [col for col in combined_df.columns if col not in device_cols and col != 'Total']
        combined_df = combined_df[device_cols + other_cols + ['Total']]
        combined_df.to_csv(output_file, index=False, sep=';')
        print(f"\nSummary saved to {output_file}")
    else:
        print("\nNo successful device summaries were generated")

if __name__ == "__main__":
    main() 
