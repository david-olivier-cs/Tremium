#!/bin/bash
# Launch script for the "tremium-hub" docker container
#
# Usage: 
#   ./launch-hub-container.sh 0 (Normal execution)
#   ./launch-hub-container.sh 1 (Run for unit test purposes)
# Notes
#   When running for unit test purposes, replace the entry point by : "CMD tail -f /dev/null"
# -----------------------------------------------------------------------------

# defining the launch policy
testing=$1

# getting docker image id for the hub container
hub_image_id=$(docker images tremium_hub_comm_container --format="{{.ID}}")

# defining the launch command
launch_command=""
if [ "$testing" -eq 1 ] 
    then 
        launch_command="sudo docker run --privileged \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/iot-communication-interface/Testing/file-transfer-hub:/tremium-hub/file-transfer-hub \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/iot-communication-interface/Testing/image-archives-hub:/tremium-hub/image-archives-hub \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/update-manager/Testing:/tremium-hub/test-update-manager \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/data-collector/Testing:/tremium-hub/test-data-collector \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v /var/run/sdp:/var/run/sdp \
            --net=host $hub_image_id"
    else
        launch_command="sudo docker run --privileged \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Mounted-volumes/image-archives-hub:/tremium-hub/image-archives-hub \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Mounted-volumes/file-transfer-hub:/tremium-hub/file-transfer-hub \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v /var/run/sdp:/var/run/sdp \
            --net=host $hub_image_id"
fi

# launching the hub container
$launch_command &

# giving time for the container to launch properly
sleep 3

# logging the hub in to the google docker registry
hub_container_id=$(docker container ps --filter "ancestor=$hub_image_id" --format "{{.ID}}")
docker exec -it $hub_container_id bash -c 'cat "$GOOGLE_APPLICATION_CREDENTIALS" | docker login -u _json_key --password-stdin https://gcr.io'