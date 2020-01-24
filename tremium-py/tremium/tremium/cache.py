import redis
import logging
from .config import NodeConfigurationManager


class NodeCacheModel():

    ''' Allows interaction with the Node's redis server (cache) '''

    conn_pool = None

    def __init__(self, config_file):

        ''' 
        Parameters
        ------
        config_file_path (str) : path to the hub configuration file 
        '''

        try : 

            # loading node configurations
            self.config_manager = NodeConfigurationManager(config_file)

            # first instance creates the connection pool, then connects
            if self.conn_pool is None: 
                
                # creating class level connection pool
                redis_config = self.config_manager.config_data["node-redis-server-config"]
                NodeCacheModel.conn_pool = redis.ConnectionPool(**redis_config)
                self.r_server = redis.StrictRedis(connection_pool=self.conn_pool)
                
                # cache vars are only initialized once
                if self.r_server.get("server_initialized") is None:
                    self._init_cache_vars()
            
            # create connection from existing connection pool
            else :
                self.r_server = redis.StrictRedis(connection_pool=self.conn_pool)

        except Exception as e:
            logging.error("NodeCacheModel failed with error : {}".format(e))
            raise


    def _init_cache_vars(self):

        ''' 
        Initializing all necessary cache variables
        *** initialization should only be done by setup scripts
        '''

        # redis server now defined as initialized
        self.r_server.set("server_initialized", "1")

        # collection flag, allows sensor data to be collected
        self.r_server.set("data_collection", "1")

        # locking flag for extracted data file
        self.r_server.set("data_file_lock", "0")

        # making sure the export request list/queue is empty
        while self.get_audio_export_request() is not None: pass


    def add_audio_export_request(self, request_str):
        self.r_server.lpush("audio_export_requests", request_str)

    def get_audio_export_request(self):

        '''
        Fetches next element in the request queue
        Returns : 
            (str or None) : export request string
        '''

        return self.r_server.rpop("audio_export_requests")


    def start_data_collection(self):
        self.r_server.set("data_collection", "1")
    
    def stop_data_collection(self):
        self.r_server.set("data_collection", "0")

    def check_data_collection(self):
        return int(self.r_server.get("data_collection")) == 1

    def lock_data_file(self):
        self.r_server.set("data_file_lock", "1")

    def unlock_data_file(self):
        self.r_server.set("data_file_lock", "0")

    def data_file_available(self):
        return int(self.r_server.get("data_file_lock")) == 0