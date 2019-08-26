'''
This script serves as an entry point to launch a bluetooth server, which runs in 
the "Communication Manager" container.

    - The bluetooth server allows Tremium Nodes to :
        - pull available updates
        - periodically transfer acquisition data 
'''

import sys
import argparse

from tremium.bluetooth import launch_hub_bluetooth_server

# parsing script arguments
parser = argparse.ArgumentParser()
parser.add_argument("config_path", help="path to the .json config file")
args = parser.parse_args()


if __name__ == "__main__" :
    launch_hub_bluetooth_server(args.config_path)