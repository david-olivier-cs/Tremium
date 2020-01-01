'''
This script is the entry point to launch the Node maintenance routine.
Should be scheduled to launch regularly (every hour by cron job)
The maintenance routine enables the node to :
    - pull available updates from the hub
    - transfer acquisition data to the hub
    - purge locally stored data
'''

import argparse
from tremium.bluetooth import launch_node_bluetooth_client

# parsing script arguments
parser = argparse.ArgumentParser()
parser.add_argument("config_path", help="path to the .json config file")
args = parser.parse_args()

if __name__ == "__main__" :
    launch_node_bluetooth_client(args.config_path)