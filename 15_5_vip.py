#!/usr/bin/env python
"""
Script to generate a report of F5 virtual servers with pool and node information
by fetching data directly from F5 API endpoints.

This script fetches data from the following F5 endpoints:
- /mgmt/tm/ltm/virtual
- /mgmt/tm/ltm/virtual/stats
- /mgmt/tm/ltm/pool
- /mgmt/tm/ltm/pool/stats
- /mgmt/tm/ltm/pool/members
- /mgmt/tm/ltm/node
- /mgmt/tm/ltm/node/stats

Generates Excel report with detailed information and summary statistics.
"""

import requests
import json
import os
from datetime import datetime
import re
from collections import defaultdict, Counter
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.auth import HTTPBasicAuth
from openpyxl import Workbook
import argparse
import logging
import sys

# Suppress insecure HTTPS warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('f5_status_report.log')
    ]
)
logger = logging.getLogger(__name__)

class F5Config:
    """Client for interacting with F5 API."""
    
    def __init__(self, host, username, password, verify_ssl=False):
        """Initialize F5 client with connection details and generate report."""
        # Ensure host has https:// prefix
        if not host.startswith('http'):
            self.F5_HOST = f"https://{host}"
        else:
            self.F5_HOST = host
            
        self.USERNAME = username
        self.PASSWORD = password
        
        # Create session
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.USERNAME, self.PASSWORD)
        self.session.verify = verify_ssl
        self.session.headers.update({'Content-Type': 'application/json'})

        # Automatically generate report upon initialization
        try:
            logger.info("Fetching virtual server data...")
            vs_data, summary_counts = process_virtual_servers(self)
            
            logger.info("Fetching pool data...")
            pool_data = process_pools(self, summary_counts)
            
            logger.info("Fetching node data...")
            node_data = process_nodes(self, summary_counts)
            
            # Generate report
            logger.info("Generating report...")
            report_data = generate_report(vs_data, pool_data, node_data)
            
            # Generate output filename prefix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            f5_hostname = self.F5_HOST.replace("https://", "").replace("http://", "")
            output_prefix = f"{f5_hostname}_{timestamp}_f5_report"
            
            # Generate Excel report
            excel_filename = generate_excel_report(report_data, summary_counts, output_prefix)
            logger.info(f"Report generated in: {os.path.abspath(os.path.dirname(excel_filename))}")
            
            # Print summary
            print("\nSummary of F5 Components:")
            print("-" * 50)
            print("Virtual Servers:")
            for status, count in summary_counts['virtual'].items():
                print(f"  {status}: {count}")
            
            print("\nPools:")
            for status, count in summary_counts['pool'].items():
                print(f"  {status}: {count}")
            
            print("\nNodes:")
            for status, count in summary_counts['node'].items():
                print(f"  {status}: {count}")
            
            print(f"\nTotal virtual servers: {len(report_data)}")
            print(f"Total pools with members: {sum(1 for item in report_data if item.get('active_members', 0) > 0)}")
            print(f"Total pools: {len(pool_data)}")
            print(f"Total nodes: {len(node_data)}")
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def get_json(self, endpoint):
        """Get data from F5 API endpoint."""
        url = f"{self.F5_HOST}{endpoint}"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get data from {endpoint}: {str(e)}")
            return None

def extract_name_from_path(path):
    """Extract the name from a path, handling different formats."""
    if '~' in path:
        parts = path.split('~')
        if len(parts) > 1:
            return parts[-1]
    
    if '/' in path:
        parts = path.split('/')
        if len(parts) > 1:
            return parts[-1]
    
    return path

def parse_destination(destination):
    """Parse destination field to extract IP and port."""
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
    
    # Remove route domain if present
    if '%' in ip:
        ip = ip.split('%')[0]
    
    return ip, port

def process_virtual_servers(f5_config):
    """Fetch and process virtual server information."""
    try:
        virtuals = f5_config.get_json('/mgmt/tm/ltm/virtual')
        vstats = f5_config.get_json('/mgmt/tm/ltm/virtual/stats')
        if not virtuals or not vstats:
            logger.error("Failed to get virtual server data or stats")
            return [], {"virtual": Counter(), "pool": Counter(), "node": Counter()}
        
        vs_data = []
        summary_counts = {
            "virtual": Counter(),
            "pool": Counter(),
            "node": Counter()
        }
        
        # Build a map from fullPath (slash and tilde) to stats
        stats_map = {}
        for key, entry in vstats.get('entries', {}).items():
            # key: https://localhost/mgmt/tm/ltm/virtual/~partition~name/stats
            parts = key.split('/')
            if len(parts) > 2:
                path = parts[-2]  # ~partition~name
                if path.startswith('~'):
                    slash_path = '/' + path.replace('~', '/')
                else:
                    slash_path = path
                stats_map[slash_path] = entry['nestedStats']['entries']
        
        for virtual in virtuals.get('items', []):
            try:
                name = virtual.get('name', '')
                fullPath = virtual.get('fullPath', '')
                partition = virtual.get('partition', '')
                
                # Try to get stats by fullPath
                stats = stats_map.get(fullPath, {})
                if not stats:
                    # Try by tilde path
                    tilde_path = '~' + fullPath.strip('/').replace('/', '~')
                    stats = stats_map.get(tilde_path, {})
                if not stats:
                    logger.warning(f"Could not get stats for virtual server: {name} ({fullPath})")
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
                
                # Update summary counts
                summary_counts["virtual"][vs_info['availabilityState']] += 1
                
                # Parse destination
                destination = virtual.get('destination', '')
                if destination:
                    ip, port = parse_destination(destination)
                    vs_info['destination_ip'] = ip
                    vs_info['destination_port'] = port
                
                vs_data.append(vs_info)
                
            except Exception as e:
                logger.error(f"Error processing virtual server {name}: {str(e)}")
                continue
        
        return vs_data, summary_counts
        
    except Exception as e:
        logger.error(f"Error in process_virtual_servers: {str(e)}")
        return [], {"virtual": Counter(), "pool": Counter(), "node": Counter()}

def process_pools(f5_config, summary_counts):
    """Fetch and process pool information using only static endpoints and membersReference."""
    try:
        pools = f5_config.get_json('/mgmt/tm/ltm/pool')
        pstats = f5_config.get_json('/mgmt/tm/ltm/pool/stats')
        if not pools or not pstats:
            logger.error("Failed to get pool data or stats")
            return {}
        
        pool_data = {}
        # Build a map from fullPath (slash and tilde) to stats
        stats_map = {}
        for key, entry in pstats.get('entries', {}).items():
            parts = key.split('/')
            if len(parts) > 2:
                path = parts[-2]  # ~partition~name
                if path.startswith('~'):
                    slash_path = '/' + path.replace('~', '/')
                else:
                    slash_path = path
                stats_map[slash_path] = entry['nestedStats']['entries']
        
        for pool in pools.get('items', []):
            try:
                fullPath = pool.get('fullPath', '')
                name = pool.get('name', '')
                partition = pool.get('partition', '')
                
                # Try to get stats by fullPath
                stats = stats_map.get(fullPath, {})
                if not stats:
                    tilde_path = '~' + fullPath.strip('/').replace('/', '~')
                    stats = stats_map.get(tilde_path, {})
                if not stats:
                    logger.warning(f"Could not get stats for pool: {name} ({fullPath})")
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
                
                # Use membersReference/link from the pool object
                members_ref = pool.get('membersReference', {}).get('link')
                if members_ref:
                    # Remove query params for version if present
                    members_ref = members_ref.split('?')[0]
                    members_data = f5_config.get_json(members_ref.replace('https://localhost', ''))
                    if members_data and 'items' in members_data:
                        for member in members_data['items']:
                            pool_data[fullPath]['members'].append({
                                'name': member.get('name', ''),
                                'address': member.get('address', ''),
                                'port': member.get('port', '')
                            })
                
            except Exception as e:
                logger.error(f"Error processing pool {name}: {str(e)}")
                continue
        
        return pool_data
        
    except Exception as e:
        logger.error(f"Error in process_pools: {str(e)}")
        return {}

def process_nodes(f5_config, summary_counts):
    """Fetch and process node information using only static endpoint /mgmt/tm/ltm/node/stats."""
    try:
        nodes = f5_config.get_json('/mgmt/tm/ltm/node')
        nstats = f5_config.get_json('/mgmt/tm/ltm/node/stats')
        if not nodes or not nstats:
            logger.error("Failed to get node data or stats")
            return {}
        
        node_data = {}
        # Build a map from fullPath (slash and tilde) to stats
        stats_map = {}
        for key, entry in nstats.get('entries', {}).items():
            parts = key.split('/')
            if len(parts) > 2:
                path = parts[-2]  # ~partition~name
                if path.startswith('~'):
                    slash_path = '/' + path.replace('~', '/')
                else:
                    slash_path = path
                stats_map[slash_path] = entry['nestedStats']['entries']
        
        for node in nodes.get('items', []):
            try:
                name = node.get('name', '')
                address = node.get('address', '')
                partition = node.get('partition', '')
                fullPath = node.get('fullPath', '')
                
                # Try to get stats by fullPath
                stats = stats_map.get(fullPath, {})
                if not stats:
                    tilde_path = '~' + fullPath.strip('/').replace('/', '~')
                    stats = stats_map.get(tilde_path, {})
                if not stats:
                    logger.warning(f"Could not get stats for node: {name} ({fullPath})")
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
                
            except Exception as e:
                logger.error(f"Error processing node {name}: {str(e)}")
                continue
        
        return node_data
        
    except Exception as e:
        logger.error(f"Error in process_nodes: {str(e)}")
        return {}

def generate_excel_report(report_data, summary_counts, output_prefix):
    """Generate Excel report with summary and details."""
    wb = Workbook()
    
    # Summary sheet
    summary_sheet = wb.active
    summary_sheet.title = "Summary"
    
    # Add summary headers
    summary_sheet.append(["Type", "Available", "Offline", "Online", "Unknown", "Total"])
    
    # Add summary data
    for k, counts in summary_counts.items():
        row = [
            k.capitalize(),
            counts.get("available", 0),
            counts.get("offline", 0),
            counts.get("online", 0),
            counts.get("unknown", 0),
            sum(counts.values())
        ]
        summary_sheet.append(row)
    
    # Details sheet
    details_sheet = wb.create_sheet("Details")
    
    # Add details headers
    headers = [
        "Virtual Server", "VS Description", "Destination", "Service Port",
        "VS Status", "VS Status Reason",
        "Pool", "Pool Status", "Pool Status Reason",
        "Active Members", "Total Members",
        "Pool Member", "Node IP", "Node Status", "Node Status Reason"
    ]
    details_sheet.append(headers)
    
    # Add details data
    for data in report_data:
        pool_info = data.get('pool', '')
        node_names = data.get('node_names', 'N/A').split('; ')
        node_addresses = data.get('node_addresses', 'N/A').split('; ')
        node_availability_states = data.get('node_availability_states', 'N/A').split('; ')
        node_status_reasons = data.get('node_status_reasons', 'N/A').split('; ')
        
        # If there are no nodes, add one row with N/A values
        if node_names == ['N/A']:
            row = [
                data['name'],
                data['description'],
                f"{data['destination_ip']}:{data['destination_port']}" if data['destination_ip'] else '',
                data['destination_port'],
                data['vs_availabilityState'],
                data['vs_statusReason'],
                data['pool_name'],
                data['pool_availabilityState'],
                data['pool_statusReason'],
                data.get('active_members', 'N/A'),
                data.get('total_members', 'N/A'),
                'N/A',  # Pool Member
                'N/A',  # Node IP
                'N/A',  # Node Status
                'N/A'   # Node Status Reason
            ]
            details_sheet.append(row)
        else:
            # Add a row for each node
            for i in range(len(node_names)):
                row = [
                    data['name'],
                    data['description'],
                    f"{data['destination_ip']}:{data['destination_port']}" if data['destination_ip'] else '',
                    data['destination_port'],
                    data['vs_availabilityState'],
                    data['vs_statusReason'],
                    data['pool_name'],
                    data['pool_availabilityState'],
                    data['pool_statusReason'],
                    data.get('active_members', 'N/A'),
                    data.get('total_members', 'N/A'),
                    node_names[i] if i < len(node_names) else 'N/A',
                    node_addresses[i] if i < len(node_addresses) else 'N/A',
                    node_availability_states[i] if i < len(node_availability_states) else 'N/A',
                    node_status_reasons[i] if i < len(node_status_reasons) else 'N/A'
                ]
                details_sheet.append(row)
    
    # Save Excel file
    excel_filename = f"{output_prefix}.xlsx"
    wb.save(excel_filename)
    logger.info(f"Excel report generated: {excel_filename}")
    return excel_filename

def generate_report(vs_data, pool_data, node_data):
    """Generate combined report data."""
    report_data = []
    
    for vs in vs_data:
        pool_path = vs.get('pool', '')
        pool_info = pool_data.get(pool_path, {})
        
        # Get node information for pool members
        node_names = []
        node_addresses = []
        node_availability_states = []
        node_enabled_states = []
        node_status_reasons = []
        
        for member in pool_info.get('members', []):
            member_address = member.get('address', '')
            node_info = node_data.get(member_address, {})
            
            if node_info:
                node_names.append(node_info['name'])
                node_addresses.append(member_address)
                node_availability_states.append(node_info['availabilityState'])
                node_enabled_states.append(node_info['enabledState'])
                node_status_reasons.append(node_info['statusReason'])
        
        report_entry = {
            # Virtual server info
            'name': vs['name'],
            'fullPath': vs['fullPath'],
            'description': vs['description'],
            'destination_ip': vs['destination_ip'],
            'destination_port': vs['destination_port'],
            
            # Virtual server status
            'vs_availabilityState': vs['availabilityState'],
            'vs_enabledState': vs['enabledState'],
            'vs_statusReason': vs['statusReason'],
            
            # Pool info
            'pool': pool_path,
            'pool_name': pool_info.get('name', ''),
            'pool_monitor': pool_info.get('monitor', ''),
            'active_members': pool_info.get('activeMemberCount', 'N/A'),
            'total_members': pool_info.get('totalMemberCount', 'N/A'),
            
            # Pool status
            'pool_availabilityState': pool_info.get('availabilityState', 'N/A'),
            'pool_enabledState': pool_info.get('enabledState', 'N/A'),
            'pool_statusReason': pool_info.get('statusReason', 'N/A'),
            
            # Node information
            'node_names': '; '.join(node_names) if node_names else 'N/A',
            'node_addresses': '; '.join(node_addresses) if node_addresses else 'N/A',
            'node_availability_states': '; '.join(node_availability_states) if node_availability_states else 'N/A',
            'node_enabled_states': '; '.join(node_enabled_states) if node_enabled_states else 'N/A',
            'node_status_reasons': '; '.join(node_status_reasons) if node_status_reasons else 'N/A'
        }
        
        report_data.append(report_entry)
    
    return report_data

def main():
    parser = argparse.ArgumentParser(description='Generate F5 status report')
    parser.add_argument('--host', required=True, help='F5 hostname or IP address')
    parser.add_argument('--username', required=True, help='F5 username')
    parser.add_argument('--password', required=True, help='F5 password')
    parser.add_argument('--verify-ssl', action='store_true', help='Verify SSL certificate')
    
    args = parser.parse_args()
    
    try:
        # Initialize F5 config
        f5_config = F5Config(args.host, args.username, args.password, args.verify_ssl)
        
        # Fetch and process data
        logger.info("Fetching virtual server data...")
        vs_data, summary_counts = process_virtual_servers(f5_config)
        
        logger.info("Fetching pool data...")
        pool_data = process_pools(f5_config, summary_counts)
        
        logger.info("Fetching node data...")
        node_data = process_nodes(f5_config, summary_counts)
        
        # Generate report
        logger.info("Generating report...")
        report_data = generate_report(vs_data, pool_data, node_data)
        
        # Generate output filename prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        f5_hostname = args.host.replace("https://", "").replace("http://", "")
        output_prefix = f"{f5_hostname}_{timestamp}_f5_report"
        
        # Generate Excel report
        excel_filename = generate_excel_report(report_data, summary_counts, output_prefix)
        logger.info(f"Report generated in: {os.path.abspath(os.path.dirname(excel_filename))}")
        
        # Print summary
        print("\nSummary of F5 Components:")
        print("-" * 50)
        print("Virtual Servers:")
        for status, count in summary_counts['virtual'].items():
            print(f"  {status}: {count}")
        
        print("\nPools:")
        for status, count in summary_counts['pool'].items():
            print(f"  {status}: {count}")
        
        print("\nNodes:")
        for status, count in summary_counts['node'].items():
            print(f"  {status}: {count}")
        
        print(f"\nTotal virtual servers: {len(report_data)}")
        print(f"Total pools with members: {sum(1 for item in report_data if item.get('active_members', 0) > 0)}")
        print(f"Total pools: {len(pool_data)}")
        print(f"Total nodes: {len(node_data)}")
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 
