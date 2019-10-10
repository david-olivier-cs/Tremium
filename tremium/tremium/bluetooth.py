import os
import os.path

import time
import logging
import datetime

import gzip

import re
import select
import socket
from multiprocessing import Process

from .config import HubConfigurationManager, NodeConfigurationManager
from .file_management import get_image_from_hub_archive
from .cache import NodeCacheModel


class NodeBluetoothClient():

    ''' Tremium Node side bluetooth client which connects to the Tremium Hub'''

    def __init__(self, config_file_path):

        '''
        Parameters
        ------
        config_file_path (str) : path to the hub configuration file
        '''

        # loading tremium node configurations
        self.config_manager = NodeConfigurationManager(config_file_path)

        # setting up logging
        log_file_path = os.path.join(self.config_manager.config_data["node-file-transfer-dir"], 
                                     self.config_manager.config_data["bluetooth-client-log-name"])
        logging.basicConfig(filename=log_file_path, filemode="a", format='%(name)s - %(levelname)s - %(message)s')
        logging.getLogger().setLevel(logging.INFO)

        # connecting to local cache
        try : self.cache = NodeCacheModel(config_file_path)
        except Exception as e:
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - NodeBluetoothClient failed to connect to cache {1}".format(time_str, e))
            raise

        # creating a connection to the hub bluetooth server
        self.server_s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.server_s.settimeout(self.config_manager.config_data["bluetooth-comm-timeout"])
        self.server_s.bind((self.config_manager.config_data["bluetooth-adapter-mac-client"],
                            self.config_manager.config_data["bluetooth-port"]))
        connection_status = self.server_s.connect_ex((self.config_manager.config_data["bluetooth-adapter-mac-server"],
                                                      self.config_manager.config_data["bluetooth-port"]))

        # handling server connection failure
        if not connection_status == 0:
            self.server_s.close()
            error_str = "NodeBluetoothClient failed to connect to server, exit code : " + str(connection_status)
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - {1}".format(time_str, error_str))
            raise ValueError(error_str)      


    def __del__(self):
        self.server_s.close()


    def store_file(self, file_name):

        ''' 
        Creates the specified file and writes the incoming server data in it.

        Params
        ------
        file_name (str) : name of the output file
        '''

        try : 

            image_archive_path = os.path.join(self.config_manager.config_data["node-image-archive-dir"], file_name)

            # writing incoming data to file
            with open(image_archive_path, "wb") as archive_file_h:

                file_data = self.server_s.recv(self.config_manager.config_data["bluetooth-message-max-size"])
                while file_data:
                    archive_file_h.write(file_data)
                    file_data = self.server_s.recv(self.config_manager.config_data["bluetooth-message-max-size"])

            self.server_s.close()

            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - Node Bluetooth client finished pulling file (socket timeout) from server : {1}\
                        ".format(time_str, self.config_manager.config_data["bluetooth-adapter-mac-server"]))

        # handling timeouts (no more data is available)
        except socket.timeout:
            self.server_s.close()
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - Node Bluetooth client finished pulling file (socket timeout) from server : {1}\
                        ".format(time_str, self.config_manager.config_data["bluetooth-adapter-mac-server"]))

        except Exception as e:

            self.server_s.close()

            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            error_str = "Node Bluetooth client failed while pulling file from server"
            server_address = self.config_manager.config_data["bluetooth-adapter-mac-server"]
            logging.error("{0} - {1} : {2}, {3}".format(time_str, error_str, server_address, e))
            raise ValueError(error_str)


    def send_data_files(self):

        ''' 
        Transfers the contents of the data-transfer folder to the hub
            1) copy the contents of the extracted data file (sensor data) to a temp file
            2) create a new extracted data file (blank) for new data extraction (sensor data)
            3) transfer/delete all data/log files to the Tremium Hub
        '''
        
        # list of tuples : (file name, file path)
        transfer_files = []

        comm_timeout = self.config_manager.config_data["bluetooth-comm-timeout"]
        transfer_dir = self.config_manager.config_data["node-file-transfer-dir"]
        transfer_file_name = self.config_manager.config_data["node-extracted-data-file"]
        data_file_max_size = self.config_manager.config_data["node-data-file-max-size"]

        archived_data_pattern_segs = self.config_manager.config_data["node-archived-data-file"].split(".")

        # when main data file is big enough transfer the contents to an other file
        data_file_path = os.path.join(transfer_dir, transfer_file_name)
        if os.stat(data_file_path).st_size > data_file_max_size : 

            # waiting for data file availability and locking it
            while not self.cache.data_file_available(): time.sleep(0.1)
            self.cache.lock_data_file()

            # renaming the filled / main data file
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            archive_file_name = archived_data_pattern_segs[0] + "-{}-".format(time_str) + archived_data_pattern_segs[1]
            archive_file_path = os.path.join(transfer_dir, archive_file_name)
            os.rename(data_file_path, archive_file_path)            

            # creating new main data file
            open(data_file_path, "w").close()

            # unlocking the data file
            self.cache.unlock_data_file()

        # collecting all (archived / ready for transfer) data files
        for element in os.listdir(transfer_dir):
            element_path = os.path.join(transfer_dir, element)
            if os.path.isfile(element_path):

                # collecting archive files and log files
                is_log_file = element.endswith(".log")
                is_archived_data = re.search(archived_data_pattern_segs[0], element) is not None
                if is_log_file or is_archived_data:
                    transfer_files.append(element, element_path)

        try :

            # going through the transfer files
            for file_info in transfer_files:
                
                # uploading the current file to the Tremium Hub
                self.server_s.send(bytes("STORE_FILE {}".format(file_info[0]), 'UTF-8'))
                time.sleep(comm_timeout + 1)
                with open(file_info[1], "rb") as image_file_h:
                    self.server_s.sendfile(image_file_h)
                time.sleep(comm_timeout + 1)

                # deleting the file after the transfer
                os.remove(file_info[1])

        except Exception as e:
            
            self.server_s.close()

            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            error_str = "Node Bluetooth client failed while uploading to server"
            server_address = self.config_manager.config_data["bluetooth-adapter-mac-server"]
            logging.error("{0} - {1} : {2}, {3}".format(time_str, error_str, server_address, e))
            raise ValueError(error_str)

            
    def launch_maintenance(self):

        ''' 
        Launches the hub - node maintenance sequence
            - transfers/purges data files (acquisition and logs)
            - fetches available updates
        '''

        try : 

            node_id = self.config_manager.config_data["node-id"]
            message_max_size = self.config_manager.config_data["bluetooth-message-max-size"]

            # sending data/log files to the tremium hub
            self.send_data_files()

            # getting list of available updates from the hub
            self.server_s.send(bytes("CHECK_AVAILABLE_UPDATES {}".format(node_id), 'UTF-8'))
            server_response = self.server_s.recv(message_max_size).decode("utf-8")
            update_files = server_response.split(",")
            

        except Exception as e:
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - Node Bluetooth client failed : {1}".format(time_str, e))



class HubServerConnectionHandler():

    ''' Server side handler of new client connections '''

    def __init__(self, config_file_path, client_s, remote_address):

        '''
        Parameters
        ----------
        config_file_path (str) : path to the hub configuration file
        client_s (socket.Socket) : socket corresponding to client connection
        remote_address (str) : client's mac adddress
        '''

        self.client_s = client_s
        self.remote_address = remote_address

        # loading tremium hub configurations
        self.config_manager = HubConfigurationManager(config_file_path)

        # setting up logging
        log_file_path = os.path.join(self.config_manager.config_data["hub-file-transfer-dir"], 
                                     self.config_manager.config_data["bluetooth-server-log-name"])
        logging.basicConfig(filename=log_file_path, filemode="a", format='%(name)s - %(levelname)s - %(message)s')
        logging.getLogger().setLevel(logging.INFO)


    def __del__(self):
        self.client_s.close()


    def handle_connection(self):

        ''' Handles interactions with the client connection '''

        # setting up monitoring for the socket
        s_data_ready = select.select([self.client_s], [], [], self.config_manager.config_data["bluetooth-comm-timeout"])

        # waiting to receive data (subject to timeout)
        if s_data_ready[0]:
    
            try : 

                # waiting and reading incoming message (blocking and subject to timeout)
                message_str = self.client_s.recv(self.config_manager.config_data["bluetooth-message-max-size"]).decode("utf-8")

                if not message_str.find("CHECK_AVAILABLE_UPDATES") == -1:
                    self.check_available_updates(message_str)

                elif not message_str.find("GET_UPDATE") == -1:
                    self.get_update(message_str)

                elif not message_str.find("STORE_FILE") == -1:
                    self.store_file(message_str)

                # handling unrecognized incoming message
                else :
                    time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
                    logging.error("{0} - Hub Bluetooth server thread connected to peer : {1}, received unrecognized message : {2}\
                                ".format(time_str, self.remote_address, message_str))
    
            except Exception as e:
                self.client_s.close()
                time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
                logging.error("{0} - Hub Bluetooth server thread connected to peer : {1}, failed to process incoming request : {2}\
                            ".format(time_str, self.remote_address, e))
    
        # closing connection with the client
        self.client_s.close()
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.info("{0} - Hub Bluetooth server thread connected to peer : {1}, closed connection\
                        ".format(time_str, self.remote_address))


    def check_available_updates(self, message_str):

        '''
        Responds with a comma seperated string containing the most recent and relevant image names
        that the node might use to update it self.
        Its up to the Node to check if the it is already up to date by analyzing the returned
        image names.
        
        Params
        ------
        message_str (str) : incoming message from client
        '''

        try : 

            # getting relevant image archives from local storage
            node_id = re.search(self.config_manager.config_data["id-pattern"], message_str).group(1)
            image_archives = get_image_from_hub_archive(node_id, self.config_manager)

            list_str = ""
            if len(image_archives) > 0:
                list_str = ",".join(image_archives)
            self.client_s.sendall(list_str.encode())

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


    def get_update(self, message_str):

        ''' 
        Transfers the specified file (in the message) to the client
        
        Parameters
        ------
        message_str (str) : incoming message from client
        '''

        try :

            # defining full path to target image file
            image_file_name = message_str.split("GET_UPDATE ")[1]
            image_file_path = os.path.join(self.config_manager.config_data["hub-image-archive-dir"], image_file_name)
            if os.path.isfile(image_file_path):

                # transafering the target file
                with open(image_file_path, "rb") as image_f:
                    self.client_s.sendfile(image_f)

            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - Hub Bluetooth server thread handled (GET_UPDATE) request from peer : {1}\
                        ".format(time_str, self.client_s.getpeername()))

        except Exception as e: 
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')                
            logging.error("{0} - Hub Bluetooth server failed while handling (GET_UPDATE) request from peer : {1}, {2}\
                        ".format(time_str, self.client_s.getpeername(), e))


    def store_file(self, message_str):

        ''' 
        Creates the specified file (in message) and writes the incoming client data in it. 
        
        Parameters
        ------
        message_str (str) : incoming message from client
        '''
    
        try :

            client_address = self.client_s.getpeername()

            # creating target image file
            target_file_name = message_str.split("STORE_FILE ")[1]
            target_file_path = os.path.join(self.config_manager.config_data["hub-file-transfer-dir"], target_file_name)
            
            with open(target_file_path, "wb") as target_file_h:

                file_data = self.client_s.recv(self.config_manager.config_data["bluetooth-message-max-size"])
                while file_data:
                    target_file_h.write(file_data)
                    file_data = self.client_s.recv(self.config_manager.config_data["bluetooth-message-max-size"])

            self.client_s.close()
            
        # handling timeouts (no more data is available)
        except socket.timeout:
            self.client_s.close()
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - Hub Bluetooth server thread handled (STORE_FILE) request from peer : {1}\
                        ".format(time_str, client_address))

        except Exception as e:
            self.client_s.close()
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - Hub Bluetooth server failed while handling (STORE_FILE) request from peer : {1}, {2}\
                        ".format(time_str, client_address, e))


def launch_hub_bluetooth_server(config_file_path):

    ''' 
    Launches the Tremium Hub bluetooth server which the Tremium Nodes connect to.

    Parameters
    ----------
    config_file_path (str) : path to the hub configuration file
    '''

    # loading Tremium Hub configurations and setting up logging
    config_manager = HubConfigurationManager(config_file_path)
    log_file_path = os.path.join(config_manager.config_data["hub-file-transfer-dir"], 
                                 config_manager.config_data["bluetooth-server-log-name"])
    logging.basicConfig(filename=log_file_path, filemode="a", format='%(name)s - %(levelname)s - %(message)s')
    logging.getLogger().setLevel(logging.INFO)

    # defining container for connection handler handles
    connection_handlers_h = []

    # creating socket to listen for new connections
    try :
        listener_s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        listener_s.bind((config_manager.config_data["bluetooth-adapter-mac-server"], 
                        config_manager.config_data["bluetooth-port"]))
        listener_s.listen()
    
        bind_address = listener_s.getsockname()
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.info("{0} - Hub Bluetooth server listening on address : {1}".format(time_str, bind_address))

    except Exception as e:
        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        logging.error("{0} - Hub Bluetooth server failed to create listener socket : {1}".format(time_str, e))
        raise

    while True:
        
        try : 

            # blocking until a new connection occurs, then create connection handler
            client_s, remote_address = listener_s.accept()
            client_s.settimeout(config_manager.config_data["bluetooth-comm-timeout"])
            connection_handler = HubServerConnectionHandler(config_file_path, client_s, remote_address)

            # launching connection handler in a seperate process
            process_h = Process(target=connection_handler.handle_connection, args=())
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