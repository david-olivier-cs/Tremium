import sys
import os.path
import unittest
import subprocess
import shutil

import time
import datetime
from google.cloud import storage
from tremium.config import HubConfigurationManager


class TestDataCollectorIntegration(unittest.TestCase):

    '''
    Holds the integration tests targetting the (Hub data collector) service
    Running the defined tests will require having the proper environment variables defined
    for the GCP API.
    '''

    # defining necessary test configurations
    launcher_script_path = os.path.join("..", "data-collector.py")
    config_file_path = os.path.join("..", "..", "..", "Config", "hub-test-config.json")
    config_manager = HubConfigurationManager(config_file_path)
    hub_transfer_dir = config_manager.config_data["hub-file-transfer-dir"]

    def test_data_collection(self):

        '''
        Test goals :
            *** this test needs an internet connection to run 
            - ensure files in the transfer folder are moved to the specified cloud bucket
            - ensure that once files are transfered, they are deleted
        '''
        
        # creating a connection to the test bucket
        storage_client = storage.Client()
        storage_bucket = storage_client.get_bucket(self.config_manager.config_data["gcp_data_bucket"])

        # creating files for testing
        test_file_names = [
            "audio-data_2018-06-01_13-57-19.json",
            "audio-data_2018-06-02_13-57-19.json",
            "audio-data_2018-06-17_13-57-19.json",
            "bluetooth-interface-logs.log"
        ]
        for file_name in test_file_names:
            file_path = os.path.join(self.hub_transfer_dir, file_name)
            open(file_path, "a").close()

        # launching the data collector
        update_manager_h = subprocess.Popen([sys.executable, self.launcher_script_path, self.config_file_path])
        update_manager_h.wait()

        # checking if the transfer directory has been cleared
        assert len(os.listdir(self.hub_transfer_dir)) == 0

        # removing any remaining files in the transfer directory
        for element in os.listdir(self.hub_transfer_dir):
            element_path = os.path.join(self.hub_transfer_dir, element)
            if os.path.isfile(element_path):
                os.remove(element_path)

        # making sure the files are written to the bucket
        # deleting the files as they are counted
        file_count = 0
        for bucket_file in storage_bucket.list_blobs():
            if(bucket_file.name in test_file_names):
                bucket_file.delete()
                file_count += 1

        assert file_count == len(test_file_names)


    def test_offline_purge(self):

        '''
        Test goals : 
            - ensure offline purging of file works properly. 
              i.e : files older then the configured amount of days are deleted
        '''

        # defining file creation parameters
        n_files = 10
        n_old_files = 4
        file_prefix = "audio-data-"
        time_limit = self.config_manager.config_data["transfer-file-max-days"]
        
        old_time = datetime.datetime.now() - datetime.timedelta(days=(time_limit + 3))
        current_time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        old_time_str = datetime.datetime.fromtimestamp(old_time.timestamp()).strftime('%Y-%m-%d_%H-%M-%S')

        # dynamically defining time stamped file names (old and new)
        test_file_names = []
        for i in range(n_files):

            file_name = file_prefix + str(i) + "_"
            if i < n_old_files: file_name += old_time_str
            else : file_name += current_time_str
            test_file_names.append(file_name)

        # creating the timestamped files
        for file_name in test_file_names:
            file_path = os.path.join(self.hub_transfer_dir, file_name)
            open(file_path, "a").close()
   
        # launching the data collector (offline mode)
        update_manager_h = subprocess.Popen([sys.executable, self.launcher_script_path, self.config_file_path, "--offline"])
        update_manager_h.wait()
        
        # making sure the proper files were deleted
        assert len(os.listdir(self.hub_transfer_dir)) == (n_files - n_old_files)

        # removing any remaining files in the transfer directory
        for element in os.listdir(self.hub_transfer_dir):
            element_path = os.path.join(self.hub_transfer_dir, element)
            if os.path.isfile(element_path):
                os.remove(element_path)


if __name__ == "__main__":
    unittest.main()