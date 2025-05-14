import requests
from requests.auth import HTTPBasicAuth
from openpyxl import Workbook
from collections import Counter
from urllib3.exceptions import InsecureRequestWarning
import datetime
import os

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class F5Config:
    def __init__(self, f5_host, username, password):
        if not f5_host.startswith('http'):
            self.F5_HOST = f"https://{f5_host}"
        else:
            self.F5_HOST = f5_host
        self.USERNAME = username
        self.PASSWORD = password
        
        # Create session
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.USERNAME, self.PASSWORD)
        self.session.verify = False
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Generate the report automatically when initialized
        self.generate_report()
    
    def get_json(self, endpoint):
        url = f"{self.F5_HOST}{endpoint}"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    def generate_report(self):
        # ==== DATA COLLECTION ====
        vs_list = self.get_json("/mgmt/tm/ltm/virtual")['items']
        summary_counts = {
            "virtual": Counter(),
            "pool": Counter(),
            "node": Counter()
        }

        details = []

        for vs in vs_list:
            vs_name = vs['name']
            vs_dest = vs.get('destination', '')
            vs_port = vs_dest.split(":")[-1] if ":" in vs_dest else ""
            vs_desc = vs.get('description', '')

            vs_stats = self.get_json(f"/mgmt/tm/ltm/virtual/{vs_name}/stats")
            vs_key = list(vs_stats['entries'].keys())[0]
            vs_data = vs_stats['entries'][vs_key]['nestedStats']['entries']
            vs_status = vs_data['status.availabilityState']['description']
            vs_reason = vs_data['status.statusReason']['description']
            summary_counts["virtual"][vs_status] += 1

            pool_path = vs.get('pool')
            if not pool_path:
                continue

            # Extract pool name and handle the path properly
            if pool_path.startswith('/'):
                # Convert '/partition/pool_name' format to API format
                pool_uri_path = pool_path.replace('/', '~')
                if pool_uri_path.startswith('~'):
                    pool_uri_path = pool_uri_path[1:]  # Remove leading ~
                pool_name = pool_path.split('/')[-1]
            else:
                # Handle case where pool might not have partition prefix
                pool_name = pool_path
                pool_uri_path = f"~Common~{pool_name}"
            
            pool_uri = f"/mgmt/tm/ltm/pool/{pool_uri_path}"
            pool_stats = self.get_json(f"{pool_uri}/stats")
            pool_key = list(pool_stats['entries'].keys())[0]
            pool_data = pool_stats['entries'][pool_key]['nestedStats']['entries']
            pool_status = pool_data['status.availabilityState']['description']
            pool_reason = pool_data['status.statusReason']['description']
            active_members = pool_data.get('activeMemberCnt', {}).get('value', 0)
            total_members = pool_data.get('memberCnt', {}).get('value', 0)
            summary_counts["pool"][pool_status] += 1

            members = self.get_json(f"{pool_uri}/members")['items']

            for member in members:
                member_name = member['name']
                node_ip = member_name.split(":")[0]

                node_stats = self.get_json(f"/mgmt/tm/ltm/node/{node_ip}/stats")
                node_key = list(node_stats['entries'].keys())[0]
                node_data = node_stats['entries'][node_key]['nestedStats']['entries']
                node_status = node_data['status.availabilityState']['description']
                node_reason = node_data['status.statusReason']['description']
                summary_counts["node"][node_status] += 1

                details.append([
                    vs_name, vs_desc, vs_dest, vs_port,
                    vs_status, vs_reason,
                    pool_name, pool_status, pool_reason,
                    active_members, total_members,
                    member_name, node_ip, node_status, node_reason
                ])

        # ==== GENERATE EXCEL ====
        wb = Workbook()
        summary_sheet = wb.active
        summary_sheet.title = "Summary"
        details_sheet = wb.create_sheet("Details")

        # Summary sheet
        summary_sheet.append(["Type", "Available", "Offline", "Online", "Unknown", "Total"])
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
        headers = [
            "Virtual Server", "VS Description", "Destination", "Service Port",
            "VS Status", "VS Status Reason", "Pool", "Pool Status", "Pool Status Reason",
            "Active Members", "Total Members", "Pool Member", "Node IP", "Node Status", "Node Status Reason"
        ]
        details_sheet.append(headers)
        for row in details:
            details_sheet.append(row)

        # Save to file
        f5_hostname = self.F5_HOST.replace("https://", "").replace("http://", "").replace("<BIG-IP-MGMT-IP>", "f5-host")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = f"{f5_hostname}_{timestamp}_vip_report.xlsx"
        wb.save(excel_path)
        print(f"Report saved to {excel_path}")
