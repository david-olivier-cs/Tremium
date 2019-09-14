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
from tremium.bluetooth import client_store_image_file
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


def create_server_connection(config_manager):

    '''
    Returns a socket connected to the bluetooth server defined in the config
    config_manager (HubConfigurationManager) : holds configurations for the Tremium Hub
    * make sure the server is launched before using this function
    ''' 

    # creating a client and connecting to server
    server_s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    server_s.settimeout(10)
    server_s.bind((config_manager.config_data["bluetooth-test-adapter-mac"],
                    config_manager.config_data["bluetooth-port"]))
    connection_status = server_s.connect_ex((config_manager.config_data["bluetooth-adapter-mac"],
                                                config_manager.config_data["bluetooth-port"]))
    
    # making sure bluetooth connection was established
    if not connection_status == 0:
        server_s.close()
        raise ValueError("Bluetooth client failed to connect to sever : {}".format(connection_status))

    return server_s


class UnitTestHubBluetoothServer(unittest.TestCase):

    ''' 
    Holds the tests for the logical components (non conectivity related) 
    elements of the Tremium Hub server.
    '''

    # defining the config information for all the unitests
    config_file_path = os.path.join("..", "..", "..", "Config", "hub-test-config.json")
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
    launcher_script_path = os.path.join("..", "bluetooth-interface.py")
    config_file_path = os.path.join("..", "..", "..", "Config", "hub-test-config.json")
    config_manager = HubConfigurationManager(config_file_path)


    def test_check_available_updates(self):

        ''' Testing the "CHECK_AVAILABLE_UPDATES" functionality '''

        # defining expected server call results
        test_node_id = "dev-test_node_machine_5"
        expected_response = "dev-test_node_machine_5_acquisition-component_2019-09-07_13-57-19.tar.gz,dev-test_node_machine_monitoring-component_2019-06-04_13-57-19.tar.gz,dev-test_node_machine_5_cache-component_2017-09-01_13-57-19.tar.gz"

        # launching the bluetooth server as a process
        server_process_h = subprocess.Popen([sys.executable, self.launcher_script_path, self.config_file_path])
        time.sleep(1)
        server_s = create_server_connection(self.config_manager)

        # calling the target functionality
        server_s.send(bytes("CHECK_AVAILABLE_UPDATES {}".format(test_node_id), 'UTF-8'))
        server_response_str = server_s.recv(self.config_manager.config_data["bluetooth-message-max-size"]).decode("utf-8")
        
        # connection clean up
        server_s.close()
        server_process_h.kill()

        # checking the server response 
        assert server_response_str == expected_response


    def test_get_update(self):

        ''' Testing the "GET_UPDATE" functionality '''

        # defining test parameters
        target_image_file = "test_get_update.tar.gz"
        target_image_path_node = os.path.join(self.config_manager.config_data["node-image-archive-dir"], 
                                              target_image_file)

        # launching the bluetooth server as a process
        server_process_h = subprocess.Popen([sys.executable, self.launcher_script_path, self.config_file_path])
        time.sleep(1)
        server_s = create_server_connection(self.config_manager)

        # calling the target functionality
        server_s.send(bytes("GET_UPDATE {}".format(target_image_file), 'UTF-8'))
        client_store_image_file(self.config_manager, server_s, target_image_file)

        # connection clean up
        server_s.close()
        server_process_h.kill()

        # checking if the file was succesfully transfered
        target_file_check = False
        for element in os.listdir(self.config_manager.config_data["node-image-archive-dir"]):
            if re.match(target_image_file, element):
                target_file_check = True
        assert target_file_check == True

        # file clean up
        os.remove(target_image_path_node)


    def test_store_file(self):

        ''' Testing the "SAVE_FILE" functionality '''

        # defining test parameters
        target_image_file = "test_data.json"
        target_image_path_node = os.path.join(self.config_manager.config_data["node-file-transfer-dir"], target_image_file)
        target_image_path_hub = os.path.join(self.config_manager.config_data["hub-file-transfer-dir"], target_image_file)

        # launching the bluetooth server as a process
        server_process_h = subprocess.Popen([sys.executable, self.launcher_script_path, self.config_file_path])
        time.sleep(1)
        server_s = create_server_connection(self.config_manager)

        # calling the target functionality and sending the target file
        server_s.send(bytes("STORE_FILE {}".format(target_image_file), 'UTF-8'))
        time.sleep(6)
        with open(target_image_path_node, "rb") as image_file_h:
            server_s.sendfile(image_file_h)

        # connection clean up
        server_s.close()
        server_process_h.kill()

        # checking if the file was succesfully transfered
        target_file_check = False
        for element in os.listdir(self.config_manager.config_data["hub-file-transfer-dir"]):
            if re.match(target_image_file, element):
                target_file_check = True
        assert target_file_check == True

        # file transfer clean up
        os.remove(target_image_path_hub)


if __name__ == '__main__':
    unittest.main()