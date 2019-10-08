import redis
import logging
from .config import NodeConfigurationManager


class NodeCacheModel():

    ''' Allows interaction with the Node's redis server (cache) '''

    # defining shared connection pool for all instances
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

            # first instance creates the connection pool
            if self.conn_pool is None: 
                redis_config = self.config_manager.config_data["node-redis-server-config"]
                NodeCacheModel.conn_pool = redis.ConnectionPool(**redis_config)

            # creating connection with the redis server
            self.r_server = redis.StrictRedis(connection_pool=self.conn_pool)

        except Exception as e:
            logging.error("NodeCacheModel failed with error : {}".format(e))
            raise


    def init_cache_vars(self):

        ''' Initializing all necessary cache variables '''

        # defining locking flag for extracted data file
        self.r_server.set("data_file_lock", "1")


    def lock_data_file(self):
        self.r_server.set("data_file_lock", "1")

    def unlock_data_file(self):
        self.r_server.set("data_file_lock", "0")

    def data_file_available(self):
        return int(self.r_server.get("data_file_lock")) == 0