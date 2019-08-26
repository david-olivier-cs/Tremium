import os.path

import time
import logging
import datetime 

import socket
from multiprocessing import Process
from .config import HubConfigurationManager


def launch_hub_bluetooth_server(config_file_path):

    ''' 
    Launches a bluetooth server which the Tremium Nodes can connect to.

    Parameters
    ----------
    config_file_path : str
        path to the hub configuration file
    '''

    # loading Tremium Hub configurations
    config_manager = HubConfigurationManager(config_file_path)

    # setting up logging
    log_file_path = os.path.join(config_manager.config_data["file-transfer-dir"], 
                                     config_manager.config_data["bluetooth-server-log-name"])
    logging.basicConfig(filename=log_file_path, filemode="a", format='%(name)s - %(levelname)s - %(message)s')
    logging.getLogger().setLevel(logging.ERROR)

    # creating socket to listen for new connections
    try : 
        listener_s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        listener_s.bind((config_manager.config_data["bluetooth-adapter-mac"], 
                        config_manager.config_data["bluetooth-port"]))
        listener_s.listen()
    
    except Exception as e:
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.error("{0} - Hub Bluetooth server failed to create listener socket : {1}".format(time_str, e))
        raise

    # loop to handle new connections
    # the "listener_s.accept()" call is blocking
    while True:

        # handling the new node connections in seperate process
        try : 
            client_s, address = listener_s.accept()
            process_h = Process(target=node_connection_handler, args=(config_file_path, client_s, address))
            process_h.start()
        
        except Exception as e: 
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - Hub Bluetooth server failed to handle incoming connection : {1}".format(time_str, e))



def node_connection_handler(config_file_path, client_s, client_address):

    '''
    Handles new client connections.

    Parameters
    ----------
    config_file_path : str
        path to the hub configuration file
    client_s : socket.Socket
        socket corresponding to client connection
    client_address : str
        client's mac adddress
    '''

    # loading Tremium Hub configurations
    config_manager = HubConfigurationManager(config_file_path)

    # testing
    while True:
        data = client_s.recv(config_manager.config_data["bluetooth-message-max-size"])
        if data: client_s.send(data)