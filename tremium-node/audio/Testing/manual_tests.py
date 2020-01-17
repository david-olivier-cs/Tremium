import os
import time
from multiprocessing import Process
from tremium.cache import NodeCacheModel
from tremium.audio import AudioDataGenerator
from tremium.config import NodeConfigurationManager

# defining test parameters
config_file_path = os.path.join("..", "..", "config", "node-test-config.json")
data_dir = "file-transfer-node"

# defining data generation entry point
def generate_data(config_file_path):
    data_generator = AudioDataGenerator(config_file_path)


if __name__ == "__main__":

    ''' Manual testing of the event detection mechanism '''

    cache = NodeCacheModel(config_file_path)
    config_manager = NodeConfigurationManager(config_file_path)

    # launching data generation in a seperate process
    process_handle = Process(target=generate_data, args=(config_file_path,))
    process_handle.start()

    # giving some time to the generator de
    time.sleep(config_manager.config_data["audio_continuous_recording_len"] + 5)
    cache.stop_data_collection()