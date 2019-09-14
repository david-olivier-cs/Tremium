import os
import os.path
import signal

import time
import logging
import datetime 

import re
import select
import socket
from multiprocessing import Process
from .config import HubConfigurationManager
from .file_management import get_image_from_hub_archive



def launch_hub_bluetooth_server(config_file_path):

    ''' 
    Launches a bluetooth server which the Tremium Nodes can connect to.

    Parameters
    ----------
    config_file_path : str
        path to the hub configuration file
    '''

    # loading Tremium Hub configurations and setting up logging
    config_manager = HubConfigurationManager(config_file_path)
    log_file_path = os.path.join(config_manager.config_data["hub-file-transfer-dir"], config_manager.config_data["bluetooth-server-log-name"])
    logging.basicConfig(filename=log_file_path, filemode="a", format='%(name)s - %(levelname)s - %(message)s')
    logging.getLogger().setLevel(logging.INFO)

    # defining container for connection handler handles
    connection_handlers_h = []

    # creating socket to listen for new connections
    try : 
        listener_s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        listener_s.bind((config_manager.config_data["bluetooth-adapter-mac"], 
                        config_manager.config_data["bluetooth-port"]))
        listener_s.listen()
    
        bind_address = listener_s.getsockname()
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.info("{0} - Hub Bluetooth server listenning on address : {1}".format(time_str, bind_address))

    except Exception as e:
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.error("{0} - Hub Bluetooth server failed to create listener socket : {1}".format(time_str, e))
        raise

    while True:
        
        try : 

            # blocking until a new client connect
            client_s, remote_address = listener_s.accept()
            client_s.settimeout(config_manager.config_data["bluetooth-comm-timeout"])

            # handling the new node connections in seperate process
            process_h = Process(target=handle_server_connection, args=(config_file_path, client_s, remote_address))
            process_h.start()
            connection_handlers_h.append(process_h)

            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - Hub Bluetooth server accepted and is handling connection from remote : {1}\
                         ".format(time_str, remote_address))

            #regular check to clear dead handles
            for handler_h in connection_handlers_h:
                if handler_h is not None:
                    connection_handlers_h.remove(handler_h)
        
        except Exception as e: 

            # killing all connection handler processes still running
            for handler_h in connection_handlers_h:
                if handler_h.exitcode is None:
                    handler_h.terminate()

            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - Hub Bluetooth server failed to handle incoming connection : {1}".format(time_str, e))
            raise



def handle_server_connection(config_file_path, client_s, remote_address):

    '''
    Handles new client connections.

    Parameters
    ----------
    config_file_path (str) : path to the hub configuration file
    client_s (socket.Socket) : socket corresponding to client connection
    remote_address (str) : client's mac adddress
    '''

    # loading Tremium Hub configurations and setting up logging
    config_manager = HubConfigurationManager(config_file_path)
    log_file_path = os.path.join(config_manager.config_data["hub-file-transfer-dir"], config_manager.config_data["bluetooth-server-log-name"])
    logging.basicConfig(filename=log_file_path, filemode="a", format='%(name)s - %(levelname)s - %(message)s')
    logging.getLogger().setLevel(logging.INFO)

    # setting up monitoring for the socket
    s_data_ready = select.select([client_s], [], [], config_manager.config_data["bluetooth-comm-timeout"])

    if s_data_ready[0]:
    
        try : 

            # waiting and reading incoming message (blocking)
            message_str = client_s.recv(config_manager.config_data["bluetooth-message-max-size"]).decode("utf-8")

            if not message_str.find("CHECK_AVAILABLE_UPDATES") == -1:
                server_check_available_updates(config_manager, message_str, client_s)

            elif not message_str.find("GET_UPDATE") == -1:
                server_get_update(config_manager, message_str, client_s)

            elif not message_str.find("STORE_FILE") == -1:
                server_store_file(config_manager, message_str, client_s)

            # handling unrecognized incoming message
            else :
                time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
                logging.error("{0} - Hub Bluetooth server thread connected to peer : {1}, received unrecognized message : {2}\
                            ".format(time_str, remote_address, message_str))
        
        except Exception as e:
            client_s.close()
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - Hub Bluetooth server thread connected to peer : {1}, failed to process incoming request : {2}\
                        ".format(time_str, remote_address, e))
    
    # closing connection with the client
    client_s.close()
    time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
    logging.info("{0} - Hub Bluetooth server thread connected to peer : {1}, closed connection\
                    ".format(time_str, remote_address))



def server_check_available_updates(config_manager, message_str, client_s):

    '''
    Responds with a comma seperated string containing the most recent and relevant image names
    that the node might use to update it self.
    Its up to the Node to check if the it is already up to date by analyzing the returned
    image names.
    Params
    ------
    config_manager (HubConfigurationManager) : holds configurations for the Tremium Hub
    message (str) : incoming message from client
    client_s (socket.Socket) : socket corresponding to client connection
    '''

    try : 

        # getting relevant image archives from local storage
        node_id = re.search(config_manager.config_data["id-pattern"], message_str).group(1)
        image_archives = get_image_from_hub_archive(node_id, config_manager)

        list_str = ""
        if len(image_archives) > 0:
            list_str = ",".join(image_archives)
        client_s.sendall(list_str.encode())

        # logging exchange
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')                
        logging.info("{0} - Hub Bluetooth server thread handled (CHECK_AVAILABLE_UPDATES) request from Node with id : {1}\
                     ".format(time_str, node_id))
        
        return list_str

    except Exception as e:

        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.error("{0} - Hub Bluetooth server thread failed while handling (CHECK_AVAILABLE_UPDATES) request from Node with id : {1}, {2}\
                      ".format(time_str, node_id, e))
        return ""



def server_get_update(config_manager, message_str, client_s):

    ''' 
    Transfers the specified file to the client
    
    Parameters
    ------
    config_manager (HubConfigurationManager) : holds configurations for the Tremium Hub
    message (str) : incoming message from client
    client_s (socket.Socket) : socket corresponding to client connection
    '''

    try :

        # defining full path to target image file
        image_file_name = message_str.split("GET_UPDATE ")[1]
        image_file_path = os.path.join(config_manager.config_data["hub-image-archive-dir"], image_file_name)
        if os.path.isfile(image_file_path):

            # transafering the target file
            with open(image_file_path, "rb") as image_f:
                client_s.sendfile(image_f)

        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.info("{0} - Hub Bluetooth server thread handled (GET_UPDATE) request from peer : {1}\
                      ".format(time_str, client_s.getpeername()))

    except Exception as e: 
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')                
        logging.error("{0} - Hub Bluetooth server failed while handling (GET_UPDATE) request from peer : {1}, {2}\
                      ".format(time_str, client_s.getpeername(), e))


def server_store_file(config_manager, message_str, client_s):

    ''' 
    Creates the specified file and writes the incoming client data in it. 
    
    Parameters
    ------
    config_manager (HubConfigurationManager) : holds configurations for the Tremium Hub
    message (str) : incoming message from client
    client_s (socket.Socket) : socket corresponding to client connection
    '''
    
    try :

        client_address = client_s.getpeername()

        # creating target image file
        target_file_name = message_str.split("STORE_FILE ")[1]
        target_file_path = os.path.join(config_manager.config_data["hub-file-transfer-dir"], target_file_name)
        
        with open(target_file_path, "wb") as target_file_h:

            file_data = client_s.recv(config_manager.config_data["bluetooth-message-max-size"])
            while file_data:
                target_file_h.write(file_data)
                file_data = client_s.recv(config_manager.config_data["bluetooth-message-max-size"])

        client_s.close()
        
    # handling timeouts (no more data is available)
    except socket.timeout:
        client_s.close()
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.info("{0} - Hub Bluetooth server thread handled (STORE_FILE) request from peer : {1}\
                     ".format(time_str, client_address))

    except Exception as e:
        client_s.close()
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.error("{0} - Hub Bluetooth server failed while handling (STORE_FILE) request from peer : {1}, {2}\
                      ".format(time_str, client_address, e))


def client_store_image_file(config_manager, server_s, file_name):

    '''
    Creates the specified file and writes the incoming server data in it.
    
    Parameters
    ------
    config_manager (HubConfigurationManager) : holds configurations for the Tremium Hub
    server_s (socket.Socket) : socket corresponding to server connection
    file_name (str) : name of the output file
    '''

    try : 

        server_address = server_s.getpeername()
        image_archive_path = os.path.join(config_manager.config_data["node-image-archive-dir"], file_name)

        # writing incoming data to file
        with open(image_archive_path, "wb") as archive_file_h:

            file_data = server_s.recv(config_manager.config_data["bluetooth-message-max-size"])
            while file_data:
                archive_file_h.write(file_data)
                file_data = server_s.recv(config_manager.config_data["bluetooth-message-max-size"])

        server_s.close()

        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.info("{0} - Node Bluetooth client finished pulling file (socket timeout) from server : {1}\
                     ".format(time_str, server_address))

    # handling timeouts (no more data is available)
    except socket.timeout:
        server_s.close()
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.info("{0} - Node Bluetooth client finished pulling file (socket timeout) from server : {1}\
                     ".format(time_str, server_address))

    except Exception as e:
        server_s.close()
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.error("{0} - Node Bluetooth client failed while pulling file from server : {1}, {2}\
                      ".format(time_str, server_address, e))