#!/bin/bash
# Launch script for the "tremium-hub" docker container
# Meant to be ran on host device start up
#
# Usage: 
#   ./launch-hub-container.sh 0 (Normal execution)
#   ./launch-hub-container.sh 1 (Run for unit test purposes)
# Notes
#   When running for unit test purposes, replace the entry point by : "CMD tail -f /dev/null"
# -----------------------------------------------------------------------------

# defining the launch policy
testing=$1

# waiting for the host device to be connected to wifi
while true; do
    LC_ALL=C nmcli -t -f DEVICE,STATE dev | grep -q "^wlo1:connected$"
    if [ $? -eq 0 ]; then
        break
    else
        sleep 1
    fi
done

# getting image id for the main hub container
hub_image_id=$(docker images gcr.io/tremium/tremium_hub_container:latest --format="{{.ID}}")

# defining the launch command for the main container
launch_command=""
home_dir="/home/one_wizard_boi"
if [ "$testing" -eq 1 ] 
    then 
        launch_command="docker run --privileged \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/iot-communication-interface/Testing/file-transfer-hub:/tremium-hub/file-transfer-hub \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/iot-communication-interface/Testing/image-archives-hub:/tremium-hub/image-archives-hub \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/update-manager/Testing:/tremium-hub/test-update-manager \
            -v /home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/communication/data-collector/Testing:/tremium-hub/test-data-collector \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v /var/run/sdp:/var/run/sdp \
            --net=host $hub_image_id"
    else
        launch_command="docker run --privileged \
            -v $home_dir/tremium-mounted-volumes/image-archives-hub:/tremium-hub/image-archives-hub \
            -v $home_dir/tremium-mounted-volumes/file-transfer-hub:/tremium-hub/file-transfer-hub \
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