import os
import sys
import os.path
import signal
import unittest
import subprocess
import shutil

import socket
from tremium.config import HubConfigurationManager


class TestBluetoothIntegration(unittest.TestCase):

    ''' Holds the integration tests targetting the (Hub bluetooth interface) '''

    def test_small_messages(self):

        '''
        Spawns a dummy bluetooth client and connects to the hub bluetooth server. The
        client emulates the behaviour of a Tremium Node.
            - ensure (hub bluetooth server) can send proper responses
        '''

        # defining test parameters and pulling configuration
        log_folder = "file-transfer"
        launcher_script_path = os.path.join("..", "bluetooth-interface.py")
        config_file_path = os.path.join("..", "..", "..", "Config", "hub-test-config.json")
        config_manager = HubConfigurationManager(config_file_path)

        # making sure the necessary output folders are created
        if os.path.exists(log_folder): shutil.rmtree(log_folder)
        os.makedirs(log_folder)

        # launching the bluetooth server
        exec_command = [sys.executable, launcher_script_path, config_file_path]
        server_process_h = subprocess.Popen(exec_command, stdout=subprocess.PIPE, 
                                            shell=True, preexec_fn=os.setsid)
    
        # creating a client socket and connecting to server
        client_s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        client_s.connect((config_manager.config_data["bluetooth-test-adapter-mac"], config_manager.config_data["bluetooth-port"]))

        # emulating Tremium Node messages
        test_message = "tremium is for BIG brains"
        client_s.send(bytes(test_message, 'UTF-8'))
        print("Received data : ")
        print(client_s.recv(config_manager.config_data["bluetooth-message-max-size"]))

        # killing the bluetooth server
        os.killpg(os.getpgid(server_process_h.pid), signal.SIGTERM)

        # clean up
        if os.path.exists(log_folder): shutil.rmtree(log_folder)


if __name__ == '__main__':
    unittest.main()