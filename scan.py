import dataclasses
import time
import socket

from typing import Optional, List
from scapy.all import arping, ARP, Ether
from tabulate import tabulate

@dataclasses.dataclass
class Device:
    mac_address: str
    ip_address: str
    hostname: str

def __scan_network(network_id: str, verbose: bool) -> List[Device]:
    scan_data: List[Device] = []

    answered, _ = arping(network_id, verbose=verbose)

    for s, r in answered:
        mac_address = r[Ether].src
        ip_address = s[ARP].pdst
        hostname = socket.getfqdn(ip_address)

        scan_data.append(Device(mac_address, ip_address, hostname))

    return scan_data

def scan_network_repeatedly(network_id: str, delay: int, verbose: bool = False):
    """ Repeatedly scan the provided network """

    while True:
        scan_data = __scan_network(network_id, verbose)
        scan_data_list = map(lambda d: [d.mac_address, d.ip_address, d.hostname], scan_data)
        print(tabulate(scan_data_list, headers=['Mac Address', 'IP Address', 'Hostname']))
        print()

        #__save_scan_data_to_dynamo_db(network_id, scan_data)

        time.sleep(delay)

if __name__ == "__main__":
    scan_network_repeatedly("192.168.1.0/24", 10)