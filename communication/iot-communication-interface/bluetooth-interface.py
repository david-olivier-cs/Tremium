'''
This script is the entry point to launch the bluetooth server, which runs continuously in 
the "communication" container.
The bluetooth server allows the nodes to :
    - pull available updates
    - periodically transfer acquisition data 
'''

import argparse
from tremium.bluetooth import launch_hub_bluetooth_server

# parsing script arguments
parser = argparse.ArgumentParser()
parser.add_argument("config_path", help="path to the .json config file")
args = parser.parse_args()

if __name__ == "__main__" :
    launch_hub_bluetooth_server(args.config_path)