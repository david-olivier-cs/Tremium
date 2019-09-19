'''
This script is meant to run as a service in the "Communication Manager" container.

    - The service listens to a dedicated "update" pub/sub topic that publishes 
      available update notifications for Tremium Node images. 
    - When the service is alerted that a new image is available, it dowloads said image 
      from Tremium's private registry and exports it to a .tar file. 
    - Further down the line the image will be transfered to the Tremium Nodes connected
      to the Hub.
'''

import time
import os.path
import logging
import argparse
import datetime

import re
import docker
import gzip
from google.cloud import pubsub_v1
from tremium.config import HubConfigurationManager

# parsing script arguments
parser = argparse.ArgumentParser()
parser.add_argument("config_path", help="path to the .json config file")
parser.add_argument("--oneshot", help="run a single update check and exit", action="store_true")
args = parser.parse_args()

if __name__ == "__main__" :

        # getting service configurations
        config_manager = HubConfigurationManager(args.config_path)

        # setting up logging for the service
        log_file_path = os.path.join(config_manager.config_data["hub-file-transfer-dir"], 
                                     config_manager.config_data["update-manager-log-name"])
        logging.basicConfig(filename=log_file_path, filemode="a", format='%(name)s - %(levelname)s - %(message)s')
        logging.getLogger().setLevel(logging.ERROR)

        # creating necessary API clients 
        docker_client = docker.Client(base_url=config_manager.config_data["docker-socket-path"])
        pubsub_subscriber = pubsub_v1.SubscriberClient()
        subscription_path = pubsub_subscriber.subscription_path(
                                        config_manager.config_data["gcp_project_id"], 
                                        config_manager.config_data["update_subscription_name"])

        # defining call back for pub/sub messages
        def update_callback(message):

            message.ack()
            new_image_path = message.data.decode("utf-8")

            # checking if hub's organisation is concerned
            image_name_pattern = config_manager.config_data["node-container-image-pattern"]
            if re.match(image_name_pattern, new_image_path) is not None :

                try : 
                  
                    pull_response = docker_client.pull(new_image_path)
                
                    # cheking if image was properly pulled
                    if "id" in pull_response :

                        # loading the pulled image
                        new_image_data = docker_client.get_image(new_image_path)

                        # defining the path of the archived image
                        time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
                        archive_name = new_image_path.split("/")[-1].split(":")[0] + "_" + time_str + ".tar"
                        archive_path = os.path.join(config_manager.config_data["hub-image-archive-dir"], archive_name)

                        # saving the pulled image to disk (.tar file)
                        with open(archive_path, 'wb') as archive_f: 
                            for chunk in new_image_data:
                                archive_f.write(chunk)

                        # compressing the archive file
                        archive_f = open(archive_path, 'rb')
                        with gzip.open(archive_path + ".gz", 'wb') as ziped_f:
                            archive_data = archive_f.read()
                            ziped_f.write(archive_data)
                        archive_f.close()                       

                        # clean up
                        os.remove(archive_path)
                        docker_client.remove_image(new_image_path)

                except Exception as e:
                    time_str = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
                    logging.error("{0} - Node update manager failed : {1}".format(time_str, e))

        pubsub_subscriber.subscribe(subscription_path, callback=update_callback)

        while True :
            time.sleep(config_manager.config_data["node-update-check-delay"])
            if args.oneshot: break