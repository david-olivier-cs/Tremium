import os
import os.path

import time
import datetime

import unittest
from tremium.audio import AudioDataGenerator
from tremium.cache import NodeCacheModel
from tremium.config import NodeConfigurationManager


class TestAudioDataGenerator(unittest.TestCase):

    ''' Holds unit/integration tests regarding the AudioDataGenerator '''

    config_file_path = os.path.join("..", "..", "config", "node-test-config.json")
    data_dir = "file-transfer-node"

    def test_audio_file_export(self):

        '''
        Sends audio export request to the export handler
            - ensures export handler can record properly
            - ensures export handler can export the requested segments
        '''

        # creating a cache (redis) connection
        cache = NodeCacheModel(self.config_file_path)

        # loading node configurations
        config_manager = NodeConfigurationManager(self.config_file_path)

        # launching the audio export handler
        data_generator = AudioDataGenerator(self.config_file_path, auto_start=False)
        data_generator.launch_audio_export_handler()

        # sending some audio export requests
        export_requests = []
        export_requests.append(str(int(time.time())) + "__5")
        cache.add_audio_export_request(export_requests[0])
        time.sleep(3)
        export_requests.append(str(int(time.time())) + "__5")
        cache.add_audio_export_request(export_requests[1])
        time.sleep(4)
        export_requests.append(str(int(time.time())) + "__5")
        cache.add_audio_export_request(export_requests[2])
        
        # waiting for recording cycle to finish + stop data collection
        time.sleep(config_manager.config_data["audio_continuous_recording_len"] + 5)
        cache.stop_data_collection()
        data_generator.join_audio_export_handler()

        # collecting all sound files in the data folder
        wav_files = []
        for data_file in os.listdir(self.data_dir):
            if data_file.endswith(".wav"):
                wav_files.append(data_file.split(".")[0])

        # checking for corresponding exports
        all_exports_present = True
        for request in export_requests:
            if not request in wav_files:
                all_exports_present = False
            else : 
                os.remove(os.path.join(self.data_dir, request + ".wav"))

        assert all_exports_present


if __name__ == "__main__":
    unittest.main()