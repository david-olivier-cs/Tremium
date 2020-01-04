import os
import os.path

import time
import logging
import datetime
import logging.handlers

import gzip

import re
import select
from bluetooth import BluetoothSocket, BluetoothError, advertise_service, find_service
from multiprocessing import Process

from .cache import NodeCacheModel
from .config import HubConfigurationManager, NodeConfigurationManager
from .file_management import get_image_from_hub_archive, get_matching_image


class NodeBluetoothClient():

    ''' Tremium Node side bluetooth client which connects to the Tremium Hub '''

    def __init__(self, config_file_path):

        '''
        Parameters
        ------
        config_file_path (str) : path to the hub configuration file
        '''

        super().__init__()

        # loading configurations
        self.config_manager = NodeConfigurationManager(config_file_path)
        log_file_path = os.path.join(self.config_manager.config_data["node-file-transfer-dir"], 
                                     self.config_manager.config_data["bluetooth-client-log-name"])
        
        # setting up logging   
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        log_handler = logging.handlers.WatchedFileHandler(log_file_path)
        log_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(log_handler)

        # defining connection to server
        self.server_s = None

        # connecting to local cache
        try : self.cache = NodeCacheModel(config_file_path)
        except Exception as e:
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - NodeBluetoothClient failed to connect to cache {1}".format(time_str, e))
            raise


    def __del__(self):

        if self.server_s is not None:
            self.server_s.close()


    def _connect_to_server(self):

        ''' Establishes a connection with the Tremium Hub Bluetooth server '''

        bluetooth_port = self.config_manager.config_data["bluetooth-port"]

        try : 

            # creating a new socket
            self.server_s = BluetoothSocket()
            self.server_s.bind((self.config_manager.config_data["bluetooth-adapter-mac-client"], bluetooth_port))

            # connecting to the hub
            time.sleep(0.25)    
            self.server_s.connect((self.config_manager.config_data["bluetooth-adapter-mac-server"], bluetooth_port))
            self.server_s.settimeout(self.config_manager.config_data["bluetooth-comm-timeout"])
            time.sleep(0.25)

        # handling server connection failure
        except Exception as e:
            self.server_s.close()
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - NodeBluetoothClient failed to connect to server : {1}".format(time_str, e))
            raise      


    def _check_available_updates(self, node_id=None):

        ''' 
        Returns list of available update images from the Hub
        
        Parameters
        ----------
        node_id (str) : node id to give hub for update checking 
        '''
        
        update_image_names = []

        if node_id is None:
            node_id = self.config_manager.config_data["node-id"] 

        try :

            # pulling list of update image names
            self._connect_to_server()
            self.server_s.send(bytes("CHECK_AVAILABLE_UPDATES {}".format(node_id), 'UTF-8'))
            response_str = self.server_s.recv(self.config_manager.config_data["bluetooth-message-max-size"]).decode("utf-8")
            update_image_names = response_str.split(",")

            # if there are no updates
            if update_image_names == [' ']:  update_image_names = []

            # logging completion
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - NodeBluetoothClient successfully checked available updates : {1}".\
                         format(time_str, str(update_image_names)))

        except Exception as e:
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - NodeBluetoothClient failed to check Hub for updates : {1}".format(time_str, e))

        self.server_s.close()
        return update_image_names


    def _get_update_file(self, update_file):

        '''
        Pulls the specified udate file from the Hub
        
        Parameters
        ----------
        update_file (str) : name of update file to fetch
        '''
       
        try : 

            # downloading file from hub
            self._connect_to_server()
            self.server_s.send(bytes("GET_UPDATE {}".format(update_file), 'UTF-8'))
            self._download_file(update_file)

            # logging completion
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - NodeBluetoothClient successfully pulled update file ({1}) from Hub\
                         ".format(time_str, update_file))

        except Exception as e:    
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - NodeBluetoothClient failed to pull update from Hub : {1}".format(time_str, e))
        
        self.server_s.close()
    

    def _download_file(self, file_name):

        ''' 
        Creates the specified file and writes the incoming Hub server data in it.
            ** assumes that the connection with the hub is already established
            ** no error handling
            ** does not close the existing connection (even if exception is thrown)
        
        Parameters
        ----------
        file_name (str) : name of the output file
        '''

        update_file_path = os.path.join(self.config_manager.config_data["node-image-archive-dir"], file_name)

        try : 

            # writing incoming data to file
            with open(update_file_path, "wb") as archive_file_h:

                file_data = self.server_s.recv(self.config_manager.config_data["bluetooth-message-max-size"])
                while file_data:
                    archive_file_h.write(file_data)
                    file_data = self.server_s.recv(self.config_manager.config_data["bluetooth-message-max-size"])

            # logging completion
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - NodeBluetoothClient successfully downloaded file ({1}) (socket timeout) from Hub\
                         ".format(time_str, file_name))

        # consider time out as : (no more available data)
        # this is the worst way of checking download is complete
        except BluetoothError: pass
    

    def _upload_file(self, file_name):

        ''' 
        Sends the specified file (from the node transfer folder) to the Hub
            ** lets exceptions bubble up 

        Parameters
        ----------
        file_name (str) : name of upload file (must be in transfer folder)
        '''

        upload_file_path = os.path.join(self.config_manager.config_data["node-file-transfer-dir"], file_name)

        try :

            self._connect_to_server()
            self.server_s.send(bytes("STORE_FILE {}".format(file_name), 'UTF-8'))

            # uploading specified file to the hub            
            with open(upload_file_path, "rb") as image_file_h:
                data = image_file_h.read(self.config_manager.config_data["bluetooth-message-max-size"])
                while data:
                    self.server_s.send(data)
                    data = image_file_h.read(self.config_manager.config_data["bluetooth-message-max-size"])
            self.server_s.close()

            # logging completion
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - NodeBluetoothClient successfully uploaded file ({1}) to Hub\
                         ".format(time_str, file_name))

        except :
            self.server_s.close()
            raise


    def _transfer_data_files(self):

        ''' 
        Transfers the contents of the data-transfer folder to the hub
            1) copy the contents of the extracted data file (sensor data) to a temp file
            2) create a new extracted data file (blank) for new data extraction (sensor data)
            3) transfer/delete all data/log files to the Tremium Hub
        '''
        
        transfer_files = []
        transfer_dir = self.config_manager.config_data["node-file-transfer-dir"]
        transfer_file_name = self.config_manager.config_data["node-extracted-data-file"]
        data_file_max_size = self.config_manager.config_data["node-data-file-max-size"]

        archived_data_pattern_segs = self.config_manager.config_data["node-archived-data-file"].split(".")

        # when the main data file is big enough transfer the contents to an other file
        data_file_path = os.path.join(transfer_dir, transfer_file_name)
        if os.path.isfile(data_file_path):
            if os.stat(data_file_path).st_size > data_file_max_size :

                # waiting for data file availability and locking it
                while not self.cache.data_file_available(): time.sleep(0.1)
                self.cache.lock_data_file()

                # renaming the filled / main data file
                time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
                archive_file_name = archived_data_pattern_segs[0] + "-{}".format(time_str) + "." + archived_data_pattern_segs[1]
                archive_file_path = os.path.join(transfer_dir, archive_file_name)
                os.rename(data_file_path, archive_file_path)            

                # creating new main data file
                open(data_file_path, "w").close()

                # unlocking the data file
                self.cache.unlock_data_file()

        # collecting all (archived / ready for transfer) data files + log files
        for element in os.listdir(transfer_dir):
            element_path = os.path.join(transfer_dir, element)
            if os.path.isfile(element_path):

                is_log_file = element.endswith(".log")
                is_archived_data = re.search(archived_data_pattern_segs[0], element) is not None
                is_full = os.stat(element_path).st_size > data_file_max_size
                if (is_log_file or is_archived_data) and is_full:
                    transfer_files.append((element, element_path))

        try :
            # uploading transfer files to the Hub and deleting them from local storage
            for file_info in transfer_files:
                self._upload_file(file_info[0])
                os.remove(file_info[1])

        except Exception as e:
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - NodeBluetoothClient failed while transfering data files : {1}".format(time_str, e))
            raise

        # return the names of files that were sent
        return [file_info[0] for file_info in transfer_files]
            

    def launch_maintenance(self):

        ''' 
        Launches the hub - node maintenance sequence
            - transfers/purges data files (acquisition and logs)
            - fetches available updates
            - adds necessary entries in the image update file
        '''

        update_entries = []
        archive_dir = self.config_manager.config_data["node-image-archive-dir"]
        time_stp_pattern = self.config_manager.config_data["image-archive-pattern"]
        docker_registry_prefix = self.config_manager.config_data["docker_registry_prefix"]

        try :

            # transfering data/log files to the hub
            self._transfer_data_files()

            # pulling available updates from the hub
            update_files = self._check_available_updates()
            for update_file in update_files:
                
                # getting old image to be updated, if any
                old_image_file = get_matching_image(update_file, self.config_manager)
                if old_image_file is not None:
                    
                    # downloading update image from the Hub
                    self._get_update_file(update_file)

                    # deleting old image archive files (.tar and .tar.gz)
                    old_image_path = os.path.join(archive_dir, old_image_file)
                    try : os.remove(old_image_path)
                    except: pass

                    # adding update file entry
                    old_image_time_stp = re.search(time_stp_pattern, old_image_file).group(3)
                    old_image_reg_path = docker_registry_prefix + old_image_file.split(old_image_time_stp)[0][ : -1]
                    update_image_time_stp = re.search(time_stp_pattern, update_file).group(3)
                    update_image_reg_path = docker_registry_prefix + update_file.split(update_image_time_stp)[0][ : -1]
                    update_entries.append(old_image_reg_path + " " + update_file + " " + update_image_reg_path + "\n")

            # if updates were pulled from the hub
            if len(update_entries) > 0:

                # halting the data collection
                self.cache.stop_data_collection()

                # logging the update entries
                time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
                logging.info("{0} - NodeBluetoothClient writting out update entries : {1}".\
                             format(time_str, str(update_entries)))

                # writing out the update entries
                with open(self.config_manager.config_data["node-image-update-file"], "w") as update_file_h:
                    for entry in update_entries:
                        update_file_h.write(entry)
                    update_file_h.write("End")

            # logging maintenance success
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - Node Bluetooth client successfully performed maintenance".format(time_str))

        except Exception as e:
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - Node Bluetooth client failed : {1}".format(time_str, e))



def launch_node_bluetooth_client(config_file_path, testing=False):

    '''
    Launches the Tremium Node bluetooth client for communication with the Hub.

    Parameters
    ----------
    config_file_path (str) : path to the hub configuration file
    testing (boolean) : 
        True : only tries once to find sever and does not run maintenance
        False : continuously tries to find the server and runs maintenance
    '''

    # loading Node configurations
    config_manager = NodeConfigurationManager(config_file_path)
    server_address = config_manager.config_data["bluetooth-adapter-mac-server"]

    # continuously checking for server device
    while True:

        # looking for the server device
        server_found = False
        for service in find_service(address=server_address):
            if service["host"] == server_address:
                server_found = True
                break

        # when server device is found, launch maintenance
        if server_found and not testing:
            node_bluetooth_client = NodeBluetoothClient(config_file_path)
            node_bluetooth_client.launch_maintenance()

        # single run exits here
        if testing : return server_found

        # delay before the next server check
        time.sleep(config_manager.config_data["bluetooth-device-check-time"])



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
        log_file_path = os.path.join(self.config_manager.config_data["hub-file-transfer-dir"], 
                                     self.config_manager.config_data["bluetooth-server-log-name"])

        # setting up logging    
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        log_handler = logging.handlers.WatchedFileHandler(log_file_path)
        log_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(log_handler)


    def __del__(self):
        self.client_s.close()


    def _check_available_updates(self, message_str):

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

            list_str = " "
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


    def _get_update(self, message_str):

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

                # transfering the target file
                with open(image_file_path, "rb") as image_f:
                    data = image_f.read(self.config_manager.config_data["bluetooth-message-max-size"])
                    while data : 
                        self.client_s.send(data)
                        data = image_f.read(self.config_manager.config_data["bluetooth-message-max-size"])

            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - Hub Bluetooth server thread handled (GET_UPDATE) request from peer : {1}\
                        ".format(time_str, self.client_s.getpeername()))

        except Exception as e: 
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')                
            logging.error("{0} - Hub Bluetooth server failed while handling (GET_UPDATE) request from peer : {1}, {2}\
                        ".format(time_str, self.client_s.getpeername(), e))


    def _store_file(self, message_str):

        ''' 
        Creates the specified file (in message) and writes the incoming client data in it. 
        
        Parameters
        ----------
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
            
        # client closes connection when all data is transfered      
        except ConnectionResetError :
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.info("{0} - Hub Bluetooth server thread handled (STORE_FILE) ({1}) request from peer : {2}\
                         ".format(time_str, target_file_name, client_address))

        except Exception as e:
            time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
            logging.error("{0} - Hub Bluetooth server failed while handling (STORE_FILE) request from peer : {1}, {2}\
                        ".format(time_str, client_address, e))


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
                    self._check_available_updates(message_str)

                elif not message_str.find("GET_UPDATE") == -1:
                    self._get_update(message_str)

                elif not message_str.find("STORE_FILE") == -1:
                    self._store_file(message_str)

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



def launch_hub_bluetooth_server(config_file_path):

    ''' 
    Launches the Tremium Hub bluetooth server which the Tremium Nodes connect to.

    Parameters
    ----------
    config_file_path (str) : path to the hub configuration file
    '''

    # loading Tremium Hub configurations
    config_manager = HubConfigurationManager(config_file_path)
    log_file_path = os.path.join(config_manager.config_data["hub-file-transfer-dir"], 
                                 config_manager.config_data["bluetooth-server-log-name"])

    # setting up logging    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_handler = logging.handlers.WatchedFileHandler(log_file_path)
    log_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(log_handler)

    # defining container for connection handler handles
    connection_handlers_h = []

    try :

        # creating socket to listen for new connections
        listener_s = BluetoothSocket()
        listener_s.bind((config_manager.config_data["bluetooth-adapter-mac-server"], 
                        config_manager.config_data["bluetooth-port"]))
        listener_s.listen(1)
    
        # advertising the listenning connection
        advertise_service(listener_s, config_manager.config_data["hub-id"])

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