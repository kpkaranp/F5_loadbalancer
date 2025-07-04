
import sys
import os

# Ajouter le répertoire parent au chemin de recherche
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../shared_modules')))

import logging
import pprint
import json
import os
import requests
import base64
import ipam
import sys
#from cyberark import CyberarkSettings, PyCyberArk
from code import interact

#def azure_hub_list_spoke_subnets(hub_vnet_id):

    # This function allocate a subnet for an aws entity spoke
    # It returns a list with :
    #   - list[0] = 0 : Automation script failed. List[1] = 'comment'. Log CRITICAL
    #   - list[0] = 1 : Allocation successful. List[1] = 'comment'. List[2] = allocated subnets. Log INFO
    #   - list[0] = 2 : Invalid request (invalid parameters). List[1] = 'comment'. Log WARNING
    #   - list[0] = 3 : Request not handled by the function. List[1] = 'comment'. Log INFO

log_level = "info"



SDS_HOST_DEV = os.environ['SDS_HOST_DEV']
SDS_LOGIN_DEV = os.environ['SDS_LOGIN_DEV']
SDS_PWD_DEV = os.environ['SDS_PWD_DEV']
HUB_ID = os.environ['HUB_ID']


   

LOG_FILE = "EXTRACTIPAM.log"

# Create instance of Ipam class
eip = ipam.Ipam(SDS_HOST_DEV, SDS_LOGIN_DEV, SDS_PWD_DEV)
tenant = ""
#Find IP blocks assigned to the Hub ID
hub_blocks = eip.get_hub_blocks(HUB_ID, tenant)
free_subnet="100.112.17.128"
subnet_prefix=29
free_parent_subnet=101865
subnet_name="vnet test"
silva_ritm="xxx"
ipam_network_exposure="external"
ipam_network_env="dev"
fw_group="AXA-Global:axa.grad.pppriv-consumer"
domain_list="ppprivmgmt.intraxa"
resp = eip.add_subnet(free_subnet, subnet_prefix, free_parent_subnet, subnet_name, silva_ritm, ipam_network_exposure, ipam_network_env, fw_group, domain_list)
    

hub_blocks_subnets = [ item['subnet_ip'] for item in hub_blocks ]
#logger.info(f'---- Found IP blocks for Hub {HUB_ID} / tenant {tenant} : {hub_blocks_subnets}')

# Loop on the entity hub blocks to list spoke subnets
spokes_subnets=[]
for hub_block in hub_blocks:
    res5 = eip.get_hub_spoke_subnets(int(hub_block['subnet_id']))
    spokes_subnets= spokes_subnets + res5

if not spokes_subnets:
    message = f'NO SPOKE FOR THE HUB'
    print("NO SPOKE FOR THE HUB")
    #logger.info(f'---- {message}')
#return [3, message]
else:
     #logger.info(f'---- {spokes_subnets}')
     dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/extracts'))
     json_file_name = os.path.join(dir, 'spoke_subnets_list_'+ str(HUB_ID) +'.json')
     print (json_file_name)
     with open(json_file_name, 'w') as json_file:
         json.dump(spokes_subnets, json_file, indent=4)
     #print (spokes_subnets)
