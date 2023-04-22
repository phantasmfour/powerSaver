# PowerSaver.py
# 04/18/2023 Shutsdown proxmox nodes and other devices during the night.

# needs pip install requests requests_toolbelt openssh_wrapper paramiko for proxmoxer
import argparse
from proxmoxer import ProxmoxAPI
from time import sleep
import subprocess
from wakeonlan import send_magic_packet

parser = argparse.ArgumentParser()

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-sd', '--shutdown', help='Shutdown Nodes',action="store_true")
group.add_argument('-su', '--startup', help='Startup Nodes',action="store_true")

args = parser.parse_args()

def shutdown_vms(prox,node):
    # Shutdown all vm's
    vmsOnNode = prox(f"nodes/{node}/qemu").get()
    #print(vmsOnNode) # Debug
    vmRunning = False # inital
    for vm in vmsOnNode:  # Check if any running
        if vm['status'] == "running":
            vmRunning = True
    if vmRunning == True:
        print(prox(f"nodes/{node}/stopall").post(node=node))  # Stop all
        x = 1
        while x == 1:
            for i in range(len(vmsOnNode)):  # For all vms on node
                if vmsOnNode[i]['status'] == "running":  # Are you running
                    sleep(1)  # wait
                    vmsOnNode = prox(f"nodes/{node}/qemu").get()  # refresh the list to see if the vm went down
                    break  # Run the for loop again to see if this vm is still running
                if i == len(vmsOnNode)-1: ## All nodes must not be running
                    print(f"All VMs on {node} have been shutdown")
                    x = 2 # Break the while loop

def shutdown_node(prox,node):
    print(prox(f"nodes/{node}/status").post(command="shutdown"))  # Shuts down the node

def wake_up_node(mac_address,node,ip):
    pingOutcome = False
    while pingOutcome == False:
        send_magic_packet(mac_address,ip_address=ip)
        print("Trying to wake")
        sleep(20)
        pingOutcome = ping(node)
        sleep(10)
    # sleep and check if we can connect.

def ping(host):
    ping_response = subprocess.run(["ping", "-c", "1", "-w", "2", host], capture_output=True)  # Ping with single count and short timeout
    return ping_response.returncode == 0

nodes = {"node1":{"mac":"ff:fd:21:5g:zw:ff","name":"node1","ip":"127.0.0.1"},"node2":{"mac":"ff:fd:21:5g:zw:ff","name":"node2","ip":"127.0.0.2"}}

if args.shutdown:
    for node in nodes:
        #print(node)
        if ping(nodes[node]["ip"]): # Make sure its on...
            prox = ProxmoxAPI(nodes[node]["ip"], user='shutdown@pve', token_name='Shutdown', token_value='12345678', verify_ssl=True, timeout=120)  # Make API session
            shutdown_vms(prox,nodes[node]["name"])  # kill vms
            shutdown_node(prox,nodes[node]["name"]) # kill bill


if args.startup:
    for node in nodes:
        if ping(nodes[node]["ip"]) == False:
            wake_up_node(nodes[node]["mac"], nodes[node]["name"],nodes[node]["ip"])

# Both the user and the api token must have the role/permissions in order for you  to have acess to the api.
# I created a custom role called ShutdownRole with Sys/VM.Audit and Sys/VM.PowerMgmt
