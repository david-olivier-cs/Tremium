'''
This script is the entry point to launch audio recording and processing.
It should be lauched by the container entry point script
'''

import argparse
from tremium.audio import AudioDataGenerator

# parsing script arguments
parser = argparse.ArgumentParser()
parser.add_argument("config_path", help="path to the .json config file")
args = parser.parse_args()

if __name__ == "__main__":
    data_generator = AudioDataGenerator(args.config_path)