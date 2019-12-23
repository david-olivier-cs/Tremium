#!/bin/bash
# Launch script for the "tremium-hub" docker container
#
# Usage: 
#   ./launch-hub-container.sh 0 (Normal execution)
#   ./launch-hub-container.sh 1 (Run for unit tests purposes)
# -----------------------------------------------------------------------------

# defining the launch policy
testing=$1

# getting docker image id for the hub container
hub_image_id=$(docker images tremium_hub_comm_container --format="{{.ID}}")

# launching the hub container
if [ "$testing" -eq 1 ] 
    then 
        sudo docker run -t -i --privileged \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/iot-communication-interface/Testing/file-transfer-hub:/tremium-hub/file-transfer-hub \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/iot-communication-interface/Testing/image-archives-hub:/tremium-hub/image-archives-hub \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/update-manager/Testing:/tremium-hub/test-update-manager \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v /var/run/sdp:/var/run/sdp \
            --net=host $hub_image_id
    else
        sudo docker run -t -i --privileged \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v /var/run/sdp:/var/run/sdp \
            --net=host $hub_image_id
fi