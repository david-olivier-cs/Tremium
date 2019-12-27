#!/bin/bash
# Launch script for the "tremium-node" docker container
#
# Usage: 
#   ./launch-hub-container.sh
# -----------------------------------------------------------------------------

# getting docker image id for the hub container
node_image_id=$(docker images dev_node_testing_01_acquisition-component --format="{{.ID}}")

# defining the launch command
launch_command="sudo docker run --privileged \
    -v /home/one_wizard_boi/Documents/Projects/Tremium/Mounted-volumes/image-archives-node:/tremium-node/image-archives-node \
    -v /home/one_wizard_boi/Documents/Projects/Tremium/Mounted-volumes/file-transfer-node:/tremium-node/file-transfer-node \
    -v /var/run/sdp:/var/run/sdp \
    --net=host $node_image_id"

# launching the hub container
$launch_command &