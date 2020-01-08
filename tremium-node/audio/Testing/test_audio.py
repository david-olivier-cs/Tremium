import os
import os.path

import time
import datetime

import unittest
from tremium.audio import AudioDataGenerator
from tremium.cache import NodeCacheModel


class TestAudioDataGenerator(unittest.TestCase):

    ''' Holds unit/integration tests regarding the AudioDataGenerator '''

    config_file_path = os.path.join("..", "..", "config", "node-test-config.json")
    data_dir = "file-transfer-node"

    @staticmethod
    def get_time_str():
        ''' Conveniance function to get time string '''
        return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')


    def test_audio_file_export(self):

        '''
        Sends audio export request to the export handler
            - ensures export handler can record properly
            - ensures export handler can export the requested segments
        '''

        # creating a cache (redis) connection
        cache = NodeCacheModel(self.config_file_path)

        # launching the audio export handler (automatic)
        data_generator = AudioDataGenerator(self.config_file_path)

        # sending some audio export requests
        export_requests = []
        export_requests.append(self.get_time_str() + "__5")
        cache.add_audio_export_request(export_requests[0])
        time.sleep(3)
        export_requests.append(self.get_time_str() + "__5")
        cache.add_audio_export_request(export_requests[1])
        time.sleep(4)
        export_requests.append(self.get_time_str() + "__5")
        cache.add_audio_export_request(export_requests[2])
        
        # waiting for recording cycle to finish + stop data collection
        time.sleep(20)
        data_generator.stop_data_collection()
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

        assert all_exports_present



if __name__ == "__main__":
    unittest.main()