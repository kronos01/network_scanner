import dataclasses
import speedtest
import time
import socket
import boto3
import os
import external
import argparse

from typing import Optional, List
from scapy.all import arping, ARP, Ether
from tabulate import tabulate

@dataclasses.dataclass
class Device:
    mac_address: str
    ip_address: str
    hostname: str
    vendor: str

@dataclasses.dataclass
class Scan:
    devices: List[Device]
    user: str
    network_id: str
    timestamp: float
    speed_test: dict

def __scan_network(network_id: str, verbose: bool) -> List[Device]:
    scan_data: List[Device] = []

    answered, _ = arping(network_id, verbose=verbose)

    for s, r in answered:
        mac_address = r[Ether].src
        ip_address = s[ARP].pdst
        hostname = socket.getfqdn(ip_address)

        scan_data.append(Device(mac_address, ip_address, hostname, external.get_mac_address_vendor(mac_address)))

    return scan_data

def __speed_test_network() -> dict:
    speedTest = speedtest.Speedtest()
    speedTest.get_best_server()

    speedTest.download()
    speedTest.upload()

    speedTest.results.share()

    return speedTest.results.dict()

def __save_scan_data_to_dynamo_db(scan: Scan):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('Scans')
    response = table.put_item(
        Item={
            'id': scan.user + '-' + scan.network_id,
            'timestamp': int(scan.timestamp),
            # TODO: bandwidth of each device
            'devices': [{
                'mac_address': d.mac_address,
                'ip_address': d.ip_address,
                'hostname': d.hostname,
                'vendor': d.vendor
            } for d in scan.devices],
            # network speed test
            'speed_test': {
                'download': str(scan.speed_test['download']),
                'upload': str(scan.speed_test['upload']),
                'ping': str(scan.speed_test['ping']),
                'bytes_sent': scan.speed_test['bytes_sent'],
                'bytes_received': scan.speed_test['bytes_received'],
                'share': scan.speed_test['share'],
                'isp': scan.speed_test['client']['isp'],
                'isprating': scan.speed_test['client']['isprating'],
                'country': scan.speed_test['client']['country'],
            }
        }
    )

    return response

def scan_network_repeatedly(user: str, network_id: str, delay: int, amount: Optional[int], verbose: bool = False):
    """ Repeatedly scan the provided network """

    scan_count = 0

    if amount == 0:
        return

    while True:
        scan_data = __scan_network(network_id, verbose)
        speed_test_data = __speed_test_network()
        scan = Scan(scan_data, user, network_id, time.time(), speed_test_data)

        __save_scan_data_to_dynamo_db(scan)
        scan_count += 1

        scan_data_list = map(lambda d: [d.mac_address, d.ip_address, d.hostname, d.vendor], scan_data)
        print(tabulate(scan_data_list,
            headers=['Mac Address', 'IP Address', 'Hostname', 'Vendor']))
        print()

        print(tabulate([[speed_test_data['download'], speed_test_data['upload'], speed_test_data['ping']]],
            headers=['Download', 'Upload', 'Ping']))
        print()

        if amount is None or scan_count < amount:
            time.sleep(delay)
        else:
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--user", help="user id associated with network", default=os.environ['USER'])
    parser.add_argument("-n", "--network", help="network id", default="192.168.1.0/24")
    parser.add_argument("-d", "--delay", help="delay in seconds between scans", type=int, default=10)
    parser.add_argument("-a", "--amount", help="number of scans, defaults to infinite", type=int, default=None)
    args = parser.parse_args()
    try:
        scan_network_repeatedly(args.user, args.network, args.delay, args.amount)
    except KeyboardInterrupt:
      print('stopped')