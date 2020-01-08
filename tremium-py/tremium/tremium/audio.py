import os
import os.path

import wave
import pyaudio

import time
import logging
import datetime
import logging.handlers

from multiprocessing import Process 

from .cache import NodeCacheModel
from .config import NodeConfigurationManager


class AudioDataGenerator():

    '''  Manages audio recording and audio feature extraction '''

    # defining audio recording parameters
    audio_chunk_size = 1024  
    sample_format = pyaudio.paInt16
    channels = 2
    fs = 44100

    def __init__(self, config_file_path):

        '''
        Parameters
        ------
        config_file_path (str) : path to the hub configuration file
        '''

        # loading configurations
        self.config_manager = NodeConfigurationManager(config_file_path)
        log_file_path = os.path.join(self.config_manager.config_data["node-file-transfer-dir"],
                                     self.config_manager.config_data["audio-data-generator-log-name"])

        # defining recording lenght parameters
        self.audio_window_max_len = self.config_manager.config_data["audio_continuous_recording_len"]
        self.audio_window_extract_len = self.config_manager.config_data["audio_event_len"]

        # defining handler process handles
        self.audio_export_handler_h = None

        # setting up logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        log_handler = logging.handlers.WatchedFileHandler(log_file_path)
        log_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(log_handler)

        # connecting to host cache server (redis)
        try: self.cache = NodeCacheModel(config_file_path)
        except Exception as e:
            time_str = self.get_timestamp_str()
            logging.error("{0} - AudioDataGenerator failed to connect to cache {1}".format(time_str, e))
            raise

        # launching the audio export handler
        self.launch_audio_recording()


    @staticmethod
    def get_timestamp_str():
        ''' Convenience function to get a time string '''
        return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')


    def stop_data_collection(self):
        self.cache.stop_data_collection()


    def launch_audio_recording(self):

        ''' Launches the audio export handler in a seperate process '''
        self.audio_export_handler_h = Process(target=self.audio_export_handler)
        self.audio_export_handler_h.start()


    def join_audio_export_handler(self):
        
        ''' Waits for the audio export handler process to end '''
        self.audio_export_handler_h.join()


    def audio_export_handler(self):

        '''
        Audio recording function, meant to be ran as a seperate process.
        Continuously records audio and handles audio export requests.
        '''

        # defining the save location for audio files
        node_data_dir = self.config_manager.config_data["node-file-transfer-dir"]

        # opening an audio stream
        port_audio = pyaudio.PyAudio()
        audio_stream = port_audio.open(format=self.sample_format,
                            channels=self.channels,
                            rate=self.fs,
                            frames_per_buffer=self.audio_chunk_size,
                            input=True)

        # continuously passing data through the frame window
        stop_recording = False 
        while not stop_recording:

            audio_frames = []

            try:

                # taking note of recording start time
                recording_start_time = time.time()

                # filling up the frame container with audio data                  
                n_chunks = int((self.fs / self.audio_chunk_size) * self.audio_window_max_len)
                for _ in range(n_chunks):
                    data = audio_stream.read(self.audio_chunk_size)
                    audio_frames.append(data)

                # collecting all audio export request, which occured before / during recording
                audio_export_requests = []
                request = self.cache.get_audio_export_request()
                while request is not None:
                    audio_export_requests.append(request)
                    request = self.cache.get_audio_export_request()
                
                # logging the received request count
                time_str = self.get_timestamp_str()
                logging.info("{0} - AudioExportHandler recevied : {1} export requests".format(time_str, len(audio_export_requests)))

                # handling audio export requests
                for export_request in audio_export_requests:

                    try :

                        audio_event_frames = []

                        # getting the offset for the start of the event
                        request_timestamp = time.mktime(datetime.datetime.strptime(export_request.split("__")[0], '%Y-%m-%d_%H-%M-%S').timetuple())
                        event_start = int(request_timestamp - recording_start_time)

                        start_frame = 0
                        end_frame = 0

                        # isolating the event data, when fully in latest recording
                        if (event_start >= 0) and (event_start < self.audio_window_max_len - self.audio_window_extract_len):
                            start_frame = (event_start * self.fs) // self.audio_chunk_size
                            end_frame = ((event_start + self.audio_window_extract_len) * self.fs) // self.audio_chunk_size
                            audio_event_frames = audio_frames[start_frame : end_frame]
                        
                        # isolating the event data, when partially passed the latest recording
                        elif (event_start >= self.audio_window_max_len - self.audio_window_extract_len) and\
                                (event_start <= self.audio_window_max_len - self.audio_window_extract_len/2):
                            start_frame = (event_start * self.fs) // self.audio_chunk_size
                            audio_event_frames = audio_frames[start_frame : ]
                    
                        # isolating the event data, when partially before the latest recording
                        elif (event_start < 0) and (event_start > 0 - self.audio_window_extract_len/2):
                            end_frame = ((event_start * self.fs) // self.audio_chunk_size) + ((self.audio_window_extract_len * self.fs) // self.audio_chunk_size)
                            audio_event_frames = audio_frames[ : end_frame]

                        # saving the isolated event audio
                        if not audio_event_frames == [] :
                            audio_file_name = os.path.join(node_data_dir, export_request + ".wav")
                            wf = wave.open(audio_file_name, 'wb')
                            wf.setnchannels(self.channels)
                            wf.setsampwidth(port_audio.get_sample_size(self.sample_format))
                            wf.setframerate(self.fs)
                            wf.writeframes(b''.join(audio_event_frames))
                            wf.close()

                    # simply skip problematic requests
                    except Exception as e:
                        time_str = self.get_timestamp_str()
                        logging.error("{0} - AudioExportHandler failed to handle export request  : {1}".format(time_str, e))

                # checking the shared flags
                if not cache.check_data_collection():
                    stop_recording = True
                    audio_stream.stop_stream()
                    audio_stream.close()
                    port_audio.terminate()

            # stopping the recoring process
            except:
                audio_stream.stop_stream()
                audio_stream.close()
                port_audio.terminate()
                stop_recording = True