import dataclasses
import time
import socket
import boto3
import os

from typing import Optional, List
from scapy.all import arping, ARP, Ether
from tabulate import tabulate

@dataclasses.dataclass
class Device:
    mac_address: str
    ip_address: str
    hostname: str

@dataclasses.dataclass
class Scan:
    devices: List[Device]
    user: str
    network_id: str
    timestamp: float

# bandwidth of each device
# network speed test
# check internet bandwidth

def __scan_network(network_id: str, verbose: bool) -> List[Device]:
    scan_data: List[Device] = []

    answered, _ = arping(network_id, verbose=verbose)

    for s, r in answered:
        mac_address = r[Ether].src
        ip_address = s[ARP].pdst
        hostname = socket.getfqdn(ip_address)

        scan_data.append(Device(mac_address, ip_address, hostname))

    return scan_data

def __save_scan_data_to_dynamo_db(scan: Scan):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('Scans')
    response = table.put_item(
        Item={
            'id': scan.user + '-' + scan.network_id,
            'timestamp': int(scan.timestamp),
            'devices': [{
                'mac_address': d.mac_address,
                'ip_address': d.ip_address,
                'hostname': d.hostname
            } for d in scan.devices]
        }
    )

    print(response)

    return response

def scan_network_repeatedly(network_id: str, delay: int, amount: Optional[int], verbose: bool = False):
    """ Repeatedly scan the provided network """

    scan_count = 0

    if amount == 0:
        return

    while True:
        scan_data = __scan_network(network_id, verbose)
        scan = Scan(scan_data, os.environ['USER'], network_id, time.time())

        __save_scan_data_to_dynamo_db(scan, )

        scan_data_list = map(lambda d: [d.mac_address, d.ip_address, d.hostname], scan_data)
        print(tabulate(scan_data_list, headers=['Mac Address', 'IP Address', 'Hostname']))
        print()

        if amount is None or scan_count < amount:
            time.sleep(delay)
        else:
            break

if __name__ == "__main__":
    scan_network_repeatedly("192.168.1.0/24", 300, 5)