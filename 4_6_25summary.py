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
import csv
from bigip_rest_client import BigipRestClient
from bigip_rest_client.exceptions import BigipRestClientException

# Suppress only the single warning from urllib3 needed.
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

def get_credentials():
    """
    Get F5 credentials from environment variables (GitHub secrets).
    """
    username = os.getenv('F5_USERNAME')
    password = os.getenv('F5_PASSWORD')
    
    if not username or not password:
        print("Error: F5_USERNAME and F5_PASSWORD environment variables must be set")
        print("Please ensure these GitHub secrets are properly configured")
        sys.exit(1)
    
    return username, password

def load_inventory():
    """Load inventory data from JSON file"""
    try:
        with open('inventory.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: inventory.json file not found")
        return None
    except json.JSONDecodeError:
        print("Error: inventory.json is not valid JSON")
        return None

def get_f5_status_summary(device_info):
    """Get status summary for a single F5 device"""
    try:
        # Initialize BigIP client
        client = BigipRestClient(
            hostname=device_info['hostname'],
            username=device_info['username'],
            password=device_info['password'],
            verify=False  # Disable SSL verification for testing
        )

        # Get virtual servers
        vs_list = client.get('/mgmt/tm/ltm/virtual')
        vs_data = []
        for vs in vs_list.get('items', []):
            vs_data.append({
                'name': vs.get('name', ''),
                'status': vs.get('enabled', False),
                'destination': vs.get('destination', ''),
                'pool': vs.get('pool', '')
            })

        # Get pools
        pool_list = client.get('/mgmt/tm/ltm/pool')
        pool_data = []
        for pool in pool_list.get('items', []):
            pool_data.append({
                'name': pool.get('name', ''),
                'status': pool.get('monitor', ''),
                'members': len(pool.get('membersReference', {}).get('items', []))
            })

        # Get nodes
        node_list = client.get('/mgmt/tm/ltm/node')
        node_data = []
        for node in node_list.get('items', []):
            node_data.append({
                'name': node.get('name', ''),
                'status': node.get('monitorStatus', ''),
                'address': node.get('address', '')
            })

        return {
            'virtual_servers': vs_data,
            'pools': pool_data,
            'nodes': node_data
        }

    except BigipRestClientException as e:
        print(f"Error connecting to {device_info['hostname']}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error for {device_info['hostname']}: {str(e)}")
        return None

def generate_summary_sheet():
    """Generate summary sheet for all F5 devices"""
    # Load inventory data
    inventory = load_inventory()
    if not inventory:
        return

    # Create output directory if it doesn't exist
    output_dir = 'f5_status_reports'
    os.makedirs(output_dir, exist_ok=True)

    # Generate timestamp for filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'f5_status_summary_{timestamp}.csv')

    # Prepare CSV headers
    headers = [
        'Datacenter',
        'Device Name',
        'Component Type',
        'Component Name',
        'Status',
        'Additional Info'
    ]

    # Write data to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        # Process each datacenter
        for dc_name, dc_data in inventory.items():
            # Process each device in the datacenter
            for device_name, device_info in dc_data.items():
                print(f"Processing {device_name} in {dc_name}...")
                
                # Get status summary for the device
                status_data = get_f5_status_summary(device_info)
                if not status_data:
                    continue

                # Write virtual server data
                for vs in status_data['virtual_servers']:
                    writer.writerow([
                        dc_name,
                        device_name,
                        'Virtual Server',
                        vs['name'],
                        'Enabled' if vs['status'] else 'Disabled',
                        f"Destination: {vs['destination']}, Pool: {vs['pool']}"
                    ])

                # Write pool data
                for pool in status_data['pools']:
                    writer.writerow([
                        dc_name,
                        device_name,
                        'Pool',
                        pool['name'],
                        pool['status'],
                        f"Members: {pool['members']}"
                    ])

                # Write node data
                for node in status_data['nodes']:
                    writer.writerow([
                        dc_name,
                        device_name,
                        'Node',
                        node['name'],
                        node['status'],
                        f"Address: {node['address']}"
                    ])

    print(f"\nSummary sheet generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Fetch F5 device status summary and save to CSV')
    parser.add_argument('--inventory', '-i', default='inventory.json',
                      help='Path to inventory JSON file (default: inventory.json)')
    parser.add_argument('--output', '-o', default='f5_status_summary.csv',
                      help='Output CSV file path (default: f5_status_summary.csv)')
    
    args = parser.parse_args()
    
    # Load device inventory
    devices = load_inventory(args.inventory)
    
    # Process each device
    all_summaries = []
    for device_info in devices:
        dc = device_info.get('dc', 'Unknown')
        device = device_info.get('device')
        name = device_info.get('name', device)
        environment = device_info.get('environment', 'Unknown')
        
        print(f"\nProcessing device: {name} ({device})")
        print(f"Datacenter: {dc}, Environment: {environment}")
        
        summary_df = get_f5_status_summary(device_info)
        
        if summary_df is not None:
            # Add device information columns
            summary_df['Datacenter'] = dc
            summary_df['Device'] = device
            summary_df['Name'] = name
            summary_df['Environment'] = environment
            
            # Add to combined summary
            all_summaries.append(summary_df)
    
    # Save combined summary if we have any successful results
    if all_summaries:
        combined_df = pd.concat(all_summaries, ignore_index=True)
        # Reorder columns to put device information first
        device_cols = ['Datacenter', 'Environment', 'Device', 'Name']
        other_cols = [col for col in combined_df.columns if col not in device_cols]
        combined_df = combined_df[device_cols + other_cols]
        combined_df.to_csv(args.output, index=False)
        print(f"\nSummary saved to {args.output}")
    else:
        print("\nNo successful device summaries were generated")

if __name__ == "__main__":
    generate_summary_sheet() 
