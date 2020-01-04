'''
This script is the entry point for the data collector component which runs periodically
in the "communication" container.
The data collector takes care of :
    - purging old data files from the hub file system
    - uploading recent data files to cloud storage
    ** data files are : log files, sensor data, ...
'''

import os
import os.path

import time
import logging
import datetime
import argparse
import logging.handlers
from google.cloud import storage

from tremium.config import HubConfigurationManager
from tremium.file_management import purge_timestamped_files

# parsing script arguments
parser = argparse.ArgumentParser()
parser.add_argument("config_path", help="path to the .json config file")
parser.add_argument("--offline", help="run offline purge of transfer files", action="store_true")
args = parser.parse_args()


def delete_log_files(target_dir):

    ''' Deletes all log files in the specified directory '''

    for element in os.listdir(target_dir):
        element_path = os.path.join(target_dir, element)
        if os.path.isfile(element_path) and element.endswith(".log"):
            os.remove(element_path)


if __name__ == "__main__":

    # loading configurations
    config_manager = HubConfigurationManager(args.config_path)
    file_transfer_dir = config_manager.config_data["hub-file-transfer-dir"]

    try : 

        # setting up logging
        log_file_path = os.path.join(file_transfer_dir, config_manager.config_data["data-collector-log-name"])
        logging.basicConfig(filename=log_file_path, filemode="a", format='%(name)s - %(levelname)s - %(message)s')    
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        log_handler = logging.handlers.WatchedFileHandler(log_file_path)
        log_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(log_handler)

        # purging old files (without transfer)
        if args.offline :

            purge_timestamped_files(file_transfer_dir, config_manager)
            delete_log_files(file_transfer_dir)

            # logging purge success
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - Successful purge of data files".format(time_str))

        # transfer to cloud bucket and purge
        else : 

            # creating google storage client
            storage_client = storage.Client()
            storage_bucket = storage_client.get_bucket(config_manager.config_data["gcp_data_bucket"])

            # going through all files in the transfer directory
            for element in os.listdir(file_transfer_dir):
                element_path = os.path.join(file_transfer_dir, element)
                if os.path.isfile(element_path):

                    # uploading the current file
                    destination_path = os.path.join(config_manager.config_data["gcp_data_bucket_path"], element)
                    blob = storage_bucket.blob(destination_path)
                    blob.upload_from_filename(element_path)

                    # deleting the current file
                    os.remove(element_path)

            # logging transfer success
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - Successful transfer of files to cloud storage".format(time_str))

    except Exception as e:

        # purging old files (without transfer)
        if not args.offline : 

            # purging .log and timestamped files
            purge_timestamped_files(file_transfer_dir, config_manager)
    
        # logging the error
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.error("{0} - Hub data collector failed with error : {1}".format(time_str, e))