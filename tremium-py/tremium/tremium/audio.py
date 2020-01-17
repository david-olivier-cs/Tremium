import os
import os.path

import wave
import pyaudio

# just for testing
import random

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

    def __init__(self, config_file_path, auto_start=True):

        '''
        Parameters
        ------
        config_file_path (str) : path to the hub configuration file
        auto_start (bool) : when true, audio recording/processing is launched from the constructor
        '''

        # loading configurations
        self.config_manager = NodeConfigurationManager(config_file_path)
        log_file_path = os.path.join(self.config_manager.config_data["node-file-transfer-dir"],
                                     self.config_manager.config_data["audio-data-generator-log-name"])

        # defining recording length parameters
        self.audio_event_len = self.config_manager.config_data["audio_event_len"]
        self.audio_event_seg_len = self.config_manager.config_data["audio_event_segment_len"]
        self.continuous_recording_len = self.config_manager.config_data["audio_continuous_recording_len"]

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

        self.cache.start_data_collection()

        # starting audio export handler and event recognition
        if auto_start:
            self.launch_audio_export_handler()
            self.start_event_recognition()
            self.join_audio_export_handler()


    @staticmethod
    def get_timestamp_str():
        ''' Convenience function to get a time string '''
        return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')


    def launch_audio_export_handler(self):

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
        recording = True
        while recording:

            audio_frames = []

            try:

                # taking note of recording start time
                recording_start_time = int(time.time())

                # filling up the frame container with audio data                  
                n_chunks = int((self.fs / self.audio_chunk_size) * self.continuous_recording_len)
                for _ in range(n_chunks):
                    data = audio_stream.read(self.audio_chunk_size)
                    audio_frames.append(data)

                # collecting all audio export request, which occured before / during recording
                audio_export_requests = []
                request = self.cache.get_audio_export_request()
                while request is not None:
                    audio_export_requests.append(request)
                    request = self.cache.get_audio_export_request()

                # handling audio export requests
                for export_request in audio_export_requests:

                    try :

                        audio_event_frames = []

                        # getting the offset for the start of the event
                        request_timestamp = int(export_request.split("__")[0])
                        event_start = int(request_timestamp - recording_start_time)

                        start_frame = 0
                        end_frame = 0

                        # isolating the event data, when fully in latest recording
                        if (event_start >= 0) and (event_start < self.continuous_recording_len - self.audio_event_len):
                            start_frame = (event_start * self.fs) // self.audio_chunk_size
                            end_frame = ((event_start + self.audio_event_len) * self.fs) // self.audio_chunk_size
                            audio_event_frames = audio_frames[start_frame : end_frame]
                        
                        # isolating the event data, when partially passed the latest recording
                        elif (event_start >= self.continuous_recording_len - self.audio_event_len) and\
                                (event_start <= self.continuous_recording_len - self.audio_event_len/2):
                            start_frame = (event_start * self.fs) // self.audio_chunk_size
                            audio_event_frames = audio_frames[start_frame : ]
                    
                        # isolating the event data, when partially before the latest recording
                        elif (event_start < 0) and (event_start > 0 - self.audio_event_len/2):
                            end_frame = ((event_start * self.fs) // self.audio_chunk_size) + ((self.audio_event_len * self.fs) // self.audio_chunk_size)
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

                # checking the shared collection flag
                if not self.cache.check_data_collection():

                    recording = False
                    audio_stream.stop_stream()
                    audio_stream.close()
                    port_audio.terminate()

                    time_str = self.get_timestamp_str()
                    logging.info("{0} - AudioExportHandler recevied signal to stop recording".format(time_str))


            # on failure, stop the recoring
            except Exception as e:

                recording = False
                self.cache.stop_data_collection()
            
                try:
                    audio_stream.stop_stream()
                    audio_stream.close()
                    port_audio.terminate()
                except : pass
                
                time_str = self.get_timestamp_str()
                logging.error("{0} - AudioExportHandler encountered fatal error : {1}".format(time_str, e))


    def start_event_recognition(self):

        ''' Launches event recognition and classification '''

        # defining the recording container
        recording_data = []

        # defining recording length (in chunks)
        n_max_chunks = int((self.fs / self.audio_chunk_size) * self.audio_event_len)
        n_segment_chunks = int((self.fs / self.audio_chunk_size) * self.audio_event_seg_len)

        # opening an audio stream
        port_audio = pyaudio.PyAudio()
        audio_stream = port_audio.open(format=self.sample_format,
                            channels=self.channels,
                            rate=self.fs,
                            frames_per_buffer=self.audio_chunk_size,
                            input=True)

        recording = True
        while recording:

            try:

                # getting the latest recording segment
                for _ in range(n_segment_chunks):
                    recording_data.append(audio_stream.read(self.audio_chunk_size))

                # once the recording window is ready for sliding
                n_remaining_chunks = n_max_chunks - len(recording_data)
                if n_remaining_chunks <= 0:

                    # trim old chunks from recorded data
                    n_remaining_chunks *= -1
                    del recording_data[0 : n_remaining_chunks]
                
                    # process the latest recording window (testing)
                    if random.random() < 0.25:
                        logging.info("Event occured")
                        # generating an event export request (test)
                        export_request = str(int(time.time())) + "__5"
                        self.cache.add_audio_export_request(export_request)

                # checking the shared collection flag
                if not self.cache.check_data_collection():

                    recording = False
                    try:
                        audio_stream.stop_stream()
                        audio_stream.close()
                        port_audio.terminate()
                    except : pass

                    time_str = self.get_timestamp_str()
                    logging.info("{0} - Event recognition recevied signal to stop recording".format(time_str))

            except Exception as e:

                recording = False
                self.cache.stop_data_collection()
                try:
                    audio_stream.stop_stream()
                    audio_stream.close()
                    port_audio.terminate()
                except: pass
                
                time_str = self.get_timestamp_str()
                logging.error("{0} - Event recognition encountered fatal error : {1}".format(time_str, e))