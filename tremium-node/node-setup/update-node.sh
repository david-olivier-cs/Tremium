#!/bin/bash
# parses the provided node update file and performs the indicated docker container updates
#
# Usage: 
#   ./update-node.sh (path to update file)
# -----------------------------------------------------------------------------

# defining node image archive directory path
archive_dir="/tremium-node/image-archives-node/"

# defining the updatefile path
update_file=$1

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
        docker container rm $old_container_id

        # deleting old image
        docker image rm $old_image_id

        # loading new image from archive file
        new_archive_path="${archive_dir}${new_image_archive}"
        echo "$new_archive_path"
        docker load -i $new_archive_path

        # launching new container
        new_image_id=$(docker images $new_image_name --format "{{.ID}}")
        docker run $new_image_id

    fi
done < "$update_file"

# once update file is completly read, crush it
echo "" > $update_file