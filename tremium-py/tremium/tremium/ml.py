import struct
import librosa
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

from .config import NodeConfigurationManager


class AudioFeatureExtractor(BaseEstimator, TransformerMixin):

    ''' 
    Allows the extraction of features from audio segments 
    
    Features : 
        - MFCCS
    '''
    
    
    def __init__(self, n_frames, n_channels, sr=44100, n_mfcc=40):
        
        # all input audio recordings have the same dimensions
        self.n_frames = n_frames
        self.n_channels = n_channels
        
        # setting recording sampling rate
        # setting the number of mfccs for extraction
        self.sr = sr
        self.n_mfcc = n_mfcc
        
        # creating vectorized scaling function for mfccs
        def scale_mfcc_array(coeff, mean):
            return np.absolute(coeff / mean)
        self.scale_mfcc_array = np.vectorize(scale_mfcc_array)
        
        
    def fit(self, X, y=None):
        return self

    
    def transform(self, X, y=None):

        '''
        Parameters
        ------
        X (bytes) : PCM byte string
        
        Returns
        -------
        (np.ndarray [shape=(n_mfcc, t)])
        '''

        # extracting scaled MFCC data (Mel-frequency cepstral coefficients)
        time_series = self._pcm_2_time_series(X)
        mfccs = librosa.feature.mfcc(y=time_series, sr=self.sr, n_mfcc=self.n_mfcc)        
        return self.scale_mfcc_array(mfccs, np.mean(np.absolute(mfccs)))
        
    
    def _pcm_2_time_series(self, byte_array):
        
        '''
        Conversion from PCM to floating point time series
        
        Parameters
        ----------
        byte_array (byte array) : PCM (16 bits) auidio data
        
        Returns
        -------
        (np.ndarray) : floating point time series
        '''
        
        time_series = np.array(struct.unpack_from("%dh" % self.n_frames * self.n_channels, byte_array))
        return time_series / 32768


class AudioClassifier():

    ''' Abstract class for audio clasifiers '''

    def __init__(self, config_file_path):
        
        '''
        Params
        ------
        config_file_path : str
            path to the Node configuration file
        '''

        # loading node configurations and classifier
        self.config_manager = NodeConfigurationManager(config_file_path) 

        # defining periodic extract parameters
        self.periodic_label = int(self.config_manager.config_data["audio-model-periodic-label"])
        self.no_event_label = int(self.config_manager.config_data["audio-model-no-event-label"])
        self.periodic_max_count = 5
        self.periodic_count = 0


    def predict(self, X):

        '''
        Returns
        -------
        int : predicted class
        '''

        pass


    def periodic_extract(self):

        ''' 
        Periodically labels the provided feature vector as a periodic extraction 
            - periodically extracted data is done for data collection
            - the input will be labelled as follows : 
                - periodic extract : 1 out of  periodic_max_count times
                - no event : the rest of the time
        '''

        # returning the apropriate label
        if self.periodic_count == 0:
            return self.periodic_label

        elif (self.periodic_count > 0) and (self.periodic_count < self.periodic_max_count): 
            return self.no_event_label 

        # counter reset
        self.periodic_count += 1
        if self.periodic_count == self.periodic_max_count:
            self.periodic_count = 0


class AuidoClassifierMFCC(AudioClassifier):

    ''' 
    MFCC based audio classifier
    Classifier trained on audio segments of this format : 
        - sampling rate : 44100
        - number of channels : 1
        - segment lenght : 176400 samples (4 seconds)
     '''

    # defining audio segment shape params (input)
    n_channels = 1
    n_samples = 176400


    def __init__(self, config_file_path):

        super().__init__(config_file_path)

        # defining audio feature extractor
        self.feature_extractor = AudioFeatureExtractor(self.n_samples, self.n_channels)
 

    def predict(self, X):

        coeffs = self.feature_extractor.transform(X)
        return 0