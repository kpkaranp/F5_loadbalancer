#!/usr/bin/env python
"""
Standalone script to generate a CSV report of F5 virtual servers with pool and node information.
Exports only the 'List' data (as in the Excel report) to a CSV file with semicolon delimiter.
"""
import requests
import csv
import argparse
from datetime import datetime
from requests.auth import HTTPBasicAuth
from collections import Counter
import os
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- F5 API Client and Data Processing ---
class F5Config:
    def __init__(self, host, username, password, verify_ssl=False):
        if not host.startswith('http'):
            self.F5_HOST = f"https://{host}"
        else:
            self.F5_HOST = host
        self.USERNAME = username
        self.PASSWORD = password
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.USERNAME, self.PASSWORD)
        self.session.verify = verify_ssl
        self.session.headers.update({'Content-Type': 'application/json'})
    def get_json(self, endpoint):
        url = f"{self.F5_HOST}{endpoint}"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

def parse_destination(destination):
    ip = ""
    port = ""
    if ':' in destination:
        parts = destination.rsplit(':', 1)
        if len(parts) == 2:
            ip_part = parts[0]
            port = parts[1]
            if '/' in ip_part:
                ip = ip_part.split('/')[-1]
            else:
                ip = ip_part
    else:
        if '/' in destination:
            ip = destination.split('/')[-1]
    if '%' in ip:
        ip = ip.split('%')[0]
    return ip, port

def process_virtual_servers(f5_config):
    virtuals = f5_config.get_json('/mgmt/tm/ltm/virtual')
    vstats = f5_config.get_json('/mgmt/tm/ltm/virtual/stats')
    stats_map = {}
    for entry in vstats.get('entries', {}).values():
        nested = entry.get('nestedStats', {}).get('entries', {})
        tm_name = nested.get('tmName', {}).get('description', '')
        if tm_name:
            stats_map[tm_name] = nested
    vs_data = []
    summary_counts = {"virtual": Counter(), "pool": Counter(), "node": Counter()}
    for virtual in virtuals.get('items', []):
        name = virtual.get('name', '')
        fullPath = virtual.get('fullPath', '')
        partition = virtual.get('partition', '')
        stats = stats_map.get(fullPath, {})
        if not stats:
            continue
        vs_info = {
            'name': name,
            'fullPath': fullPath,
            'partition': partition,
            'description': virtual.get('description', ''),
            'destination_ip': '',
            'destination_port': '',
            'pool': virtual.get('pool', ''),
            'availabilityState': stats.get('status.availabilityState', {}).get('description', 'N/A'),
            'enabledState': stats.get('status.enabledState', {}).get('description', 'N/A'),
            'statusReason': stats.get('status.statusReason', {}).get('description', 'N/A')
        }
        summary_counts["virtual"][vs_info['availabilityState']] += 1
        destination = virtual.get('destination', '')
        if destination:
            ip, port = parse_destination(destination)
            vs_info['destination_ip'] = ip
            vs_info['destination_port'] = port
        vs_data.append(vs_info)
    return vs_data, summary_counts

def process_pools(f5_config, summary_counts):
    pools = f5_config.get_json('/mgmt/tm/ltm/pool')
    pstats = f5_config.get_json('/mgmt/tm/ltm/pool/stats')
    stats_map = {}
    for entry in pstats.get('entries', {}).values():
        nested = entry.get('nestedStats', {}).get('entries', {})
        tm_name = nested.get('tmName', {}).get('description', '')
        if tm_name:
            stats_map[tm_name] = nested
    pool_data = {}
    for pool in pools.get('items', []):
        fullPath = pool.get('fullPath', '')
        name = pool.get('name', '')
        partition = pool.get('partition', '')
        stats = stats_map.get(fullPath, {})
        if not stats:
            continue
        availability_state = stats.get('status.availabilityState', {}).get('description', 'N/A')
        summary_counts["pool"][availability_state] += 1
        pool_data[fullPath] = {
            'name': name,
            'partition': partition,
            'monitor': pool.get('monitor', ''),
            'availabilityState': availability_state,
            'enabledState': stats.get('status.enabledState', {}).get('description', 'N/A'),
            'statusReason': stats.get('status.statusReason', {}).get('description', 'N/A'),
            'activeMemberCount': stats.get('activeMemberCnt', {}).get('value', 0),
            'totalMemberCount': stats.get('memberCnt', {}).get('value', 0),
            'members': []
        }
        members_ref = pool.get('membersReference', {}).get('link')
        if members_ref:
            members_ref = members_ref.split('?')[0]
            if members_ref.startswith('https://localhost'):
                members_ref = members_ref.replace('https://localhost', '')
            members_data = f5_config.get_json(members_ref)
            if members_data and 'items' in members_data:
                for member in members_data['items']:
                    pool_data[fullPath]['members'].append({
                        'name': member.get('name', ''),
                        'address': member.get('address', ''),
                        'state': member.get('state', ''),
                        'session': member.get('session', '')
                    })
    return pool_data

def process_nodes(f5_config, summary_counts):
    nodes = f5_config.get_json('/mgmt/tm/ltm/node')
    nstats = f5_config.get_json('/mgmt/tm/ltm/node/stats')
    stats_map = {}
    for entry in nstats.get('entries', {}).values():
        nested = entry.get('nestedStats', {}).get('entries', {})
        tm_name = nested.get('tmName', {}).get('description', '')
        if tm_name:
            stats_map[tm_name] = nested
    node_data = {}
    for node in nodes.get('items', []):
        name = node.get('name', '')
        address = node.get('address', '')
        partition = node.get('partition', '')
        fullPath = node.get('fullPath', '')
        stats = stats_map.get(fullPath, {})
        if not stats:
            continue
        availability_state = stats.get('status.availabilityState', {}).get('description', 'N/A')
        summary_counts["node"][availability_state] += 1
        node_data[address] = {
            'name': name,
            'fullPath': fullPath,
            'partition': partition,
            'availabilityState': availability_state,
            'enabledState': stats.get('status.enabledState', {}).get('description', 'N/A'),
            'statusReason': stats.get('status.statusReason', {}).get('description', 'N/A')
        }
    return node_data

def generate_report(vs_data, pool_data, node_data):
    report_data = []
    for vs in vs_data:
        pool_path = vs.get('pool', '')
        pool_info = pool_data.get(pool_path, {})
        report_entry = {
            'name': vs['name'],
            'fullPath': vs['fullPath'],
            'description': vs['description'],
            'destination_ip': vs['destination_ip'],
            'destination_port': vs['destination_port'],
            'vs_availabilityState': vs['availabilityState'],
            'vs_enabledState': vs['enabledState'],
            'vs_statusReason': vs['statusReason'],
            'pool': pool_path,
            'pool_name': pool_info.get('name', ''),
            'pool_monitor': pool_info.get('monitor', ''),
            'active_members': pool_info.get('activeMemberCount', ''),
            'total_members': pool_info.get('totalMemberCount', ''),
            'pool_availabilityState': pool_info.get('availabilityState', ''),
            'pool_enabledState': pool_info.get('enabledState', ''),
            'pool_statusReason': pool_info.get('statusReason', ''),
        }
        report_data.append(report_entry)
    return report_data

# --- CSV Export Logic ---
CSV_HEADERS = [
    "Load Balancer", "Data Center", "Tier",
    "Virtual Server", "VS Description", "VS Destination", "VS Service Port",
    "VS Status", "VS Status Reason",
    "Pool Name", "Pool Status", "Pool Status Reason",
    "Pool Active Members", "Pool Total Members",
    "Member Name", "Member Address", "Member State", "Member Session",
    "Node Status", "Node Status Reason", "Node Enabled State"
]

def main():
    parser = argparse.ArgumentParser(description='Export F5 List data to CSV')
    parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL certificate')
    parser.add_argument('--output-dir', default='.', help='Directory to save CSV files')
    args = parser.parse_args()

    username = os.environ.get('API_USERNAME')
    password = os.environ.get('API_PASSWORD')
    if not username or not password:
        raise ValueError("API_USERNAME and API_PASSWORD environment variables must be set")

    with open('inventory.json', 'r') as f:
        devices = json.load(f)

    all_rows = []

    for device in devices:
        host = device.get('mgmt_ip') or device.get('device')
        if not host:
            print(f"Skipping device with missing mgmt_ip or device field: {device}")
            continue
        f5_config = F5Config(host, username, password, args.verify_ssl)
        vs_data, summary_counts = process_virtual_servers(f5_config)
        pool_data = process_pools(f5_config, summary_counts)
        node_data = process_nodes(f5_config, summary_counts)
        report_data = generate_report(vs_data, pool_data, node_data)

        for data in report_data:
            pool_info = data.get('pool', '')
            pool_members = []
            if pool_info in pool_data:
                pool_members = pool_data[pool_info].get('members', [])
            if not pool_members:
                row = [
                    device.get('device', ''),
                    device.get('dc', ''),
                    device.get('tier', ''),
                    data['name'],
                    data['description'],
                    f"{data['destination_ip']}:{data['destination_port']}" if data['destination_ip'] else '',
                    data['destination_port'],
                    data['vs_availabilityState'],
                    data['vs_statusReason'],
                    data['pool_name'],
                    data['pool_availabilityState'],
                    data['pool_statusReason'],
                    data.get('active_members', ''),
                    data.get('total_members', ''),
                    '',  # Member Name
                    '',  # Member Address
                    '',  # Member State
                    '',  # Member Session
                    '',  # Node Status
                    '',  # Node Status Reason
                    ''   # Node Enabled State
                ]
                all_rows.append(row)
            else:
                for member in pool_members:
                    member_address = member.get('address', '')
                    node_info = node_data.get(member_address, {})
                    row = [
                        device.get('device', ''),
                        device.get('dc', ''),
                        device.get('tier', ''),
                        data['name'],
                        data['description'],
                        f"{data['destination_ip']}:{data['destination_port']}" if data['destination_ip'] else '',
                        data['destination_port'],
                        data['vs_availabilityState'],
                        data['vs_statusReason'],
                        data['pool_name'],
                        data['pool_availabilityState'],
                        data['pool_statusReason'],
                        data.get('active_members', ''),
                        data.get('total_members', ''),
                        member.get('name', ''),
                        member.get('address', ''),
                        member.get('state', ''),
                        member.get('session', ''),
                        node_info.get('availabilityState', ''),
                        node_info.get('statusReason', ''),
                        node_info.get('enabledState', '')
                    ]
                    all_rows.append(row)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(
        args.output_dir,
        f"f5vpmn_summary{timestamp}.csv"
    )
    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(CSV_HEADERS)
        writer.writerows(all_rows)
    print(f"CSV file created: {output_file}")

if __name__ == "__main__":
    main() 
