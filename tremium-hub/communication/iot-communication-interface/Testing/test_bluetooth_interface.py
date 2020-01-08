import re
import mock
import unittest

import os
import sys
import time
import signal
import socket
import os.path
import subprocess

from tremium.config import HubConfigurationManager
from tremium.bluetooth import NodeBluetoothClient, launch_node_bluetooth_client
from tremium.file_management import get_image_from_hub_archive


def mocked_listdir(path):

    ''' mock implementation of the os.listdir function '''

    return [
        "dev-test_node_machine_5_acquisition-component_2019-09-07_13-57-19.tar.gz",
        "dev-test_node_machine_5_acquisition-component_2019-09-01_13-57-19.tar.gz",
        "dev-test_node_machine_5_cache-component_2017-09-01_13-57-19.tar.gz",
        "dev-test_node_machine_monitoring-component_2019-06-04_13-57-19.tar.gz",
        "dev-test_node_machine_5_monitoring-component_2019-06-02_13-57-19.tar.gz",
        "dev-node-test-latest.tar.gz"
    ]


def mocked_isfile(path):
    ''' mock implementation of the os.path.isfile function '''
    return True


class UnitTestHubBluetoothServer(unittest.TestCase):

    ''' 
    Holds the tests for the logical components (non conectivity related) 
    elements of the Tremium Hub server.
    '''

    # defining the config information for all the unitests
    config_file_path = os.path.join("..", "..", "..", "config", "hub-test-config.json")
    config_manager = HubConfigurationManager(config_file_path)

    @mock.patch('os.path.isfile', side_effect=mocked_isfile)
    @mock.patch('os.listdir', side_effect=mocked_listdir)
    def test_archive_file_fetch(self, listdir_function, isfile_function):

        ''' Testing the "get_image_from_hub_archive" function '''

        # defining the expected result
        expected_image_files = [
            "dev-test_node_machine_5_acquisition-component_2019-09-07_13-57-19.tar.gz",
            "dev-test_node_machine_5_cache-component_2017-09-01_13-57-19.tar.gz",
            "dev-test_node_machine_monitoring-component_2019-06-04_13-57-19.tar.gz"
        ]

        test_node_id = "dev-test_node_machine_5"
        recevied_image_files = get_image_from_hub_archive(test_node_id, self.config_manager)

        # cecking for the right file names
        check_passed = len(recevied_image_files) == len(expected_image_files)
        for img_file in recevied_image_files :
            if not img_file in expected_image_files:
                check_passed = False
                break

        assert check_passed == True


class IntegrationTestHubBluetoothServer(unittest.TestCase):

    ''' 
    Holds the integration tests targetting the (Hub bluetooth interface) 
    The connectivity aspects are tested via a dummy bluetooth client that connects to the server
    The client is meant to emulate the behaviour of a tremium node
    * To run these tests, the host machine needs 2 bluetooth cinterfaces
    '''

    # defining necessary test configurations
    config_file_path = os.path.join("..", "..", "..", "config", "hub-test-config.json")
    config_manager = HubConfigurationManager(config_file_path)
            
    def test_check_available_updates(self):

        ''' Testing the Hub bluetooth server's "CHECK_AVAILABLE_UPDATES" functionality '''

        # defining expected server call results
        test_node_id = "dev-test_node_machine_5"
        expected_response = "dev-test_node_machine_5_acquisition-component_2019-09-07_13-57-19.tar.gz,dev-test_node_machine_monitoring-component_2019-06-04_13-57-19.tar.gz,dev-test_node_machine_5_cache-component_2017-09-01_13-57-19.tar.gz"

        # making sure returned file names are as expected 
        node_bluetooth_client = NodeBluetoothClient(self.config_file_path)
        assert node_bluetooth_client._check_available_updates(test_node_id) == expected_response.split(",")


    def test_get_update(self):

        ''' Testing the Hub bluetooth server's "GET_UPDATE" functionality '''

        # defining test parameters
        target_image_file = "dev_node_testing_01_acquisition-component_2019-09-07_13-57-19.tar.gz"
        archive_dir = self.config_manager.config_data["node-image-archive-dir"]
        target_image_path_node = os.path.join(archive_dir, target_image_file)

        # pulling test update file from Hub
        node_bluetooth_client = NodeBluetoothClient(self.config_file_path)
        node_bluetooth_client._get_update_file(target_image_file)

        # making sure the specified file was downloaded
        assert target_image_file in os.listdir(archive_dir)
        os.remove(target_image_path_node)


    def test_store_file(self):

        ''' Testing the Hub bluetooth server's "SAVE_FILE" functionality '''

        # defining test parameters
        test_file = "test_data.json"
        hub_transfer_dir = self.config_manager.config_data["hub-file-transfer-dir"]
        target_image_path_hub = os.path.join(hub_transfer_dir, test_file)

        # uploading test file to the hub
        node_bluetooth_client = NodeBluetoothClient(self.config_file_path)
        node_bluetooth_client._upload_file(test_file)

        # checking if the file was succesfully transfered and clean up
        assert test_file in os.listdir(hub_transfer_dir)
        os.remove(target_image_path_hub)


    def test_send_data_files(self):

        ''' Testing transfer of data from the Tremium Node (NodeBluetoothClient._send_data_files) '''

        data_file_name = self.config_manager.config_data["node-extracted-data-file"]
        node_transfer_dir = self.config_manager.config_data["node-file-transfer-dir"]

        def create_data_file(lines):
            
            ''' Generates a data file with the specified amount of lines '''

            data_file_path = os.path.join(node_transfer_dir, data_file_name)
            with open(data_file_path, "w") as data_f:
                for _ in range(lines): data_f.write("test\n")

        def check_hub_for_files(file_names):
            
            ''' Checks if specified files were transfered to the Tremium Hub, and deletes them '''
            
            result = True
            hub_transfer_dir = self.config_manager.config_data["hub-file-transfer-dir"] 
            hub_transfer_files = os.listdir(hub_transfer_dir)
            
            for file_name in file_names:
                if file_name in hub_transfer_files:
                    os.remove(os.path.join(hub_transfer_dir, file_name))
                else : result = False
            
            return result

        node_bluetooth_client = NodeBluetoothClient(self.config_file_path)

        # triggering transfer with sufficiently sized data file
        create_data_file(40)
        transfered_files = node_bluetooth_client._transfer_data_files()
        time.sleep(0.5)
        assert check_hub_for_files(transfered_files)
         
        # triggering transfer with insufficiently sized data file
        create_data_file(2)
        transfered_files = node_bluetooth_client._transfer_data_files()
        time.sleep(0.5)
        assert check_hub_for_files(transfered_files)

        # final clean up
        os.remove(os.path.join(node_transfer_dir, data_file_name))


    def test_node_maintenance(self):

        ''' Testing interactions with the Tremium Node (NodeBluetoothClient.launch_maintenance) '''

        node_archive_dir = self.config_manager.config_data["node-image-archive-dir"]
        docker_registry_prefix = self.config_manager.config_data["docker_registry_prefix"] 

        # defining test parameters
        update_image_zip = "dev_node_testing_01_acquisition-component_2019-09-07_13-57-19.tar.gz"
        update_listing_path = os.path.join(".", self.config_manager.config_data["node-image-update-file"])
    
        # creating necessary artifacts (1)
        old_image_zip_file = "dev_node_testing_01_acquisition-component_2014-06-20_13-57-19.tar.gz"
        old_image_zip_path = os.path.join(node_archive_dir, old_image_zip_file)
        old_image_tar_path = old_image_zip_path[ : -3] 
        with open(old_image_zip_path, "w") as old_image_h:
            old_image_h.write(" ")
        with open(old_image_tar_path, "w") as old_image_h:
            old_image_h.write(" ")

        # defining expected return (1)
        expected_listing = docker_registry_prefix + "dev_node_testing_01_acquisition-component "
        expected_listing += update_image_zip + " "
        expected_listing += docker_registry_prefix + "dev_node_testing_01_acquisition-component\nEnd" 

        # launching hub maintenance and checking update listing (1)
        node_bluetooth_client = NodeBluetoothClient(self.config_file_path)
        node_bluetooth_client.launch_maintenance()
        with open(update_listing_path, "r") as update_listing_h:
            assert expected_listing.rstrip() == update_listing_h.read().rstrip()

        # cleaning up
        os.remove(update_listing_path)
        os.remove(os.path.join(node_archive_dir, update_image_zip))


    def test_server_advertising(self):

        ''' Checks if the Bluetooth server properly advertises its self '''
        
        assert launch_node_bluetooth_client(self.config_file_path, testing=True)
        self.test_check_available_updates()


if __name__ == '__main__':

    # set to True if server is running from docker container
    server_from_docker = False

    if not server_from_docker:

        # defining Tremium Hub Bluetooth server params
        config_file_path = os.path.join("..", "..", "..", "config", "hub-test-config.json")
        launcher_script_path = os.path.join("..", "bluetooth-interface.py")

        # launching the Tremium Hub bluetooth server as a seperate process
        server_process_h = subprocess.Popen([sys.executable, launcher_script_path, config_file_path])
        time.sleep(3)

    # executing the unit tests and killing server
    unittest.main()
    if not server_from_docker: server_process_h.kill()