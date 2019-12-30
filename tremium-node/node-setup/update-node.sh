#!/bin/bash
# parses the node update file and performs the indicated docker container updates
#
# Usage: 
#   ./update-node.sh
# -----------------------------------------------------------------------------

# defining node image archive directory path
archive_dir="$HOME/Tremium-mounted-volumes/image-archives-node/"
update_file="$HOME/Tremium-mounted-volumes/image-archives-node/node-image-updates.txt"
node_startup_script="$HOME/launch-node-container.sh"

# making sure the update file is not currently being edited
end_tag=$(tail -1 $update_file | head -1)
if [ "$end_tag" != "End" ]
    then
        exit 1
fi

# processing the lines of the update file
while IFS= read -r line
do
    # not processing the last line
    if [ "$line" != "End" ]
        then

        # parsing update details
        old_image_name=$(echo $line | cut -f1 -d ' ')
        new_image_archive=$(echo $line | cut -f2 -d ' ')
        new_image_name=$(echo $line | cut -f3 -d ' ')

        # getting old ids
        old_image_id=$(docker images $old_image_name --format "{{.ID}}")
        old_container_id=$(docker container ps --filter "ancestor=$old_image_id" --format "{{.ID}}")

        # stopping and deleting old container
        docker container stop $old_container_id
        docker container rm -f $old_container_id

        # deleting old image
        docker image rm -f $old_image_id

        # loading new image from archive file
        new_archive_path="${archive_dir}${new_image_archive}"
        docker load -i $new_archive_path

        # launching new container
        new_image_id=$(docker images $new_image_name --format "{{.ID}}")
        launch_command="${node_startup_script} ${new_image_id}"
        $launch_command

    fi
done < "$update_file"

# once update file is completly read, crush it
sudo rm $update_file && echo "" >> $update_file