#!/bin/bash
# Launch script for the "tremium-node" docker containers
# Meant to be ran on host device start up
#
# Usage: 
#   ./launch-hub-container.sh
#    or
#   ./launch-hub-container.sh (image id)
# -----------------------------------------------------------------------------

# defining optional target image id
target_image_id=""
target_image_id=$1

# getting docker image id for the acquisition component
node_image_id=$(docker images gcr.io/tremium/dev_node_testing_01_acquisition-component:latest --format="{{.ID}}")

# defining launch command for the acquisition component
home_dir="/home/one_wizard_boi"
launch_command="sudo docker run --privileged \
    -v $home_dir/tremium-mounted-volumes/image-archives-node:/tremium-node/image-archives-node \
    -v $home_dir/tremium-mounted-volumes/file-transfer-node:/tremium-node/file-transfer-node \
    -v /var/run/sdp:/var/run/sdp \
    --device /dev/snd:/dev/snd \
    --net=host $node_image_id"

# launching mechanism
if [ "$target_image_id" != "" ]
    
    # launching only the target container (update context)
    then
        if [ "$target_image_id" == "$node_image_id" ]
            then
                $launch_command &
        fi

    # launching all the containers (start up context)
    else
        $launch_command &
fi

