import sys
import os.path
import unittest
import subprocess
import shutil

import re
import docker
from google.cloud import pubsub_v1
from tremium.config import HubConfigurationManager


class TestUpdateManagerIntegration(unittest.TestCase):

    '''
    Holds the integration tests targetting the (Node update manager) service
    Running the defined tests will require having the proper environment variables defined
    for the GCP API aswell has the proper priveleges to run docker commands.
    '''

    def test_new_node_image_pull(self):

        '''
        Publishes a dummy image to the tremium image registry and sends and update message
        to the (node update manager).
            *** this test needs an internet connection to run
            - ensure (node update manager) can consume pub/sub
            - ensure (node update manager) can pull new images
            - ensure (node update manager) can save new image to file
        '''

        # defining test parameters and pulling configuration
        config_file_path = os.path.join("..", "..", "..", "Config", "hub-test-config.json")
        config_manager = HubConfigurationManager(config_file_path)
        manager_script_path = os.path.join("..", "update-manager.py")
        docker_build_dir = os.path.join(".", "dummy-app")
        test_image_tag = "gcr.io/tremium/dev_node_test:latest"
        image_output_folder = config_manager.config_data["hub-image-archive-dir"]
        log_folder = config_manager.config_data["hub-file-transfer-dir"]
        

        docker_client = docker.Client(base_url=config_manager.config_data["docker-socket-path"])
        pubsub_publisher = pubsub_v1.PublisherClient()
        update_topic_path = pubsub_publisher.topic_path(config_manager.config_data["gcp_project_id"],
                                                        config_manager.config_data["update_topic_name"])

        # making sure the necessary output folders are created
        if os.path.exists(log_folder): shutil.rmtree(log_folder)
        if os.path.exists(image_output_folder): shutil.rmtree(image_output_folder)
        os.makedirs(log_folder)
        os.makedirs(image_output_folder)
    
        # creating test image and pushing it to remote registry
        [ _ for _ in docker_client.build(path=docker_build_dir, tag=test_image_tag)]
        [ _ for _ in  docker_client.push(test_image_tag)]
        docker_client.remove_image(test_image_tag)

        # sending an image update message to the update manager
        pubsub_publisher.publish(update_topic_path, data=test_image_tag.encode("utf-8"))

        # starting the node update manager
        update_manager_h = subprocess.Popen([sys.executable, manager_script_path, config_file_path, "--oneshot"])
        update_manager_h.wait()

        # checking if the updated image was downloaded
        file_name_pattern = test_image_tag.split("/")[-1].split(":")[0]
        assert re.search(file_name_pattern, os.listdir(image_output_folder)[0]) is not None 

        # clean up
        if os.path.exists(log_folder): shutil.rmtree(log_folder)
        if os.path.exists(image_output_folder): shutil.rmtree(image_output_folder)


if __name__ == '__main__':
    unittest.main()