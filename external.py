import requests
import time


def get_mac_address_vendor(mac_address: str, retries: int = 10) -> str:
    """  """
    # Can also use https://macvendors.co/api/{mac_address} for a richer payload
    prefix = ''.join(mac_address.split(':')[0:3])
    response = requests.get(f'https://macvendors.com/query/{prefix}')

    if response.status_code == 200:
        return response.text
    elif retries <= 0:
        return ""
    else:
        time.sleep(0.5)
        return get_mac_address_vendor(mac_address, retries - 1)