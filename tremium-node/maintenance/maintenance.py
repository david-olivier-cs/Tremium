'''
This script is the entry point to launch the Node maintenance routine.
The maintenance routine enables the node to :
    - pull available updates from the hub
    - transfer acquisition data to the hub
    - purge locally stored data
'''

import argparse
from tremium.bluetooth import NodeBluetoothClient

# parsing script arguments
parser = argparse.ArgumentParser()
parser.add_argument("config_path", help="path to the .json config file")
args = parser.parse_args()

if __name__ == "__main__" :
    node_bluetooth_client = NodeBluetoothClient(args.config_path)
    node_bluetooth_client.launch_maintenance()
