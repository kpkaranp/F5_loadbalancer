def vip_status(self):
    BIGIP_IP = self.address
    AUTH_TOKEN = self.token

    headers = {
        "X-F5-Auth-Token": AUTH_TOKEN,
        "Content-Type": "application/json"
    }

    def get_virtuals():
        url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual"
        r = requests.get(url, headers=headers, verify=False)
        r.raise_for_status()
        return r.json().get('items', [])

    def get_virtual_stats():
        url = f"https://{BIGIP_IP}/mgmt/tm/ltm/virtual/stats"
        r = requests.get(url, headers=headers, verify=False)
        r.raise_for_status()
        return r.json().get('entries', {})

    def get_pools():
        url = f"https://{BIGIP_IP}/mgmt/tm/ltm/pool"
        r = requests.get(url, headers=headers, verify=False)
        r.raise_for_status()
        return r.json().get('items', [])

    def get_pool_stats():
        url = f"https://{BIGIP_IP}/mgmt/tm/ltm/pool/stats"
        r = requests.get(url, headers=headers, verify=False)
        r.raise_for_status()
        return r.json().get('entries', {})

    def get_pool_members(pool_full_path):
        pool_uri = pool_full_path.replace('/', '~')
        url = f"https://{BIGIP_IP}/mgmt/tm/ltm/pool/{pool_uri}/members"
        r = requests.get(url, headers=headers, verify=False)
        if r.status_code == 200:
            return r.json().get('items', [])
        return []

    virtuals = get_virtuals()
    stats = get_virtual_stats()
    pools = get_pools()
    pool_stats = get_pool_stats()

    # Build VS info map by name only
    vs_info_map = {}
    for stat in stats.values():
        nested = stat.get('nestedStats', {}).get('entries', {})
        name = nested.get('tmName', {}).get('description', '')
        dest = nested.get('destination', {}).get('description', '')
        status = nested.get('status.availabilityState', {}).get('description', '')
        status_desc = nested.get('status.statusReason', {}).get('description', '')
        port = dest.split(':')[-1] if ':' in dest else 'N/A'
        vs_info_map[name] = {
            'destination': dest,
            'port': port,
            'status': status,
            'status_desc': status_desc
        }

    # Build pool info map by name only
    pool_info_map = {}
    for stat in pool_stats.values():
        nested = stat.get('nestedStats', {}).get('entries', {})
        name = nested.get('tmName', {}).get('description', '')
        status = nested.get('status.availabilityState', {}).get('description', '')
        status_desc = nested.get('status.statusReason', {}).get('description', '')
        active_members = nested.get('activeMemberCount', {}).get('value', 0)
        total_members = nested.get('memberCount', {}).get('value', 0)
        pool_info_map[name] = {
            'status': status,
            'status_desc': status_desc,
            'active_members': active_members,
            'total_members': total_members
        }

    # Map VS name to pool and description
    vs_pool_map = {}
    vs_desc_map = {}
    for vs in virtuals:
        vs_name = vs['name']
        pool = vs.get('pool', None)
        if pool:
            if pool.startswith('/'):
                pool_name = pool.split('/')[-1]
            else:
                pool_name = pool
            vs_pool_map[vs_name] = pool_name
        desc = vs.get('description', '')
        vs_desc_map[vs_name] = desc

    # Collect all data
    all_rows = []
    for pool in pools:
        pool_name = pool['name']
        members = get_pool_members(pool['fullPath'])
        pool_info = pool_info_map.get(pool_name, {})
        # Find which VSs use this pool
        linked_vs_names = [k for k, v in vs_pool_map.items() if v == pool_name]
        if not linked_vs_names:
            linked_vs_names = ['Unlinked']
        for vs_name in linked_vs_names:
            vs_info = vs_info_map.get(vs_name, {})
            row_base = {
                'Virtual Server': vs_name,
                'VS Description': vs_desc_map.get(vs_name, ''),
                'Destination': vs_info.get('destination', ''),
                'Service Port': vs_info.get('port', ''),
                'VS Status': vs_info.get('status', ''),
                'VS Status Reason': vs_info.get('status_desc', ''),
                'Pool': pool_name,
                'Pool Status': pool_info.get('status', ''),
                'Pool Status Reason': pool_info.get('status_desc', ''),
                'Active Members': pool_info.get('active_members', 0),
                'Total Members': pool_info.get('total_members', 0)
            }
            if members:
                for member in members:
                    all_rows.append({
                        **row_base,
                        'Pool Member': member.get('name'),
                        'Node IP': member.get('address', 'N/A'),
                        'Member Status': member.get('state', 'unknown'),
                        'Session': member.get('session', 'unknown')
                    })
            else:
                all_rows.append({
                    **row_base,
                    'Pool Member': 'No Members',
                    'Node IP': '-',
                    'Member Status': '-',
                    'Session': '-'
                })
    # Save to Excel
    df = pd.DataFrame(all_rows)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{BIGIP_IP}_f5_summary_{timestamp}_vsnameonly.xlsx"
    df.to_excel(filename, index=False)
    print(f"Excel file saved: {filename}") 
