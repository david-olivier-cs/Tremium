import re
import os
import os.path

import time
import datetime

def get_image_from_hub_archive(node_id, config_manager):
    
    '''
    Returns list of names of locally stored image files
    The returned images file names correspond to the most recent image files that are
    relevant to the specified id. 
    Params
    ------
    node_id (str) : id of the Tremium Node asking for an update.
    config_manager (HubConfigurationManager) : holds configurations for the Tremium Hub 
    '''

    matched_image_files = {}
    image_archive_dir = config_manager.config_data["hub-image-archive-dir"]

    # going through all archived image files
    for archive_element in os.listdir(image_archive_dir):
        archive_element_path = os.path.join(image_archive_dir, archive_element)
        if os.path.isfile(archive_element_path) and archive_element.endswith(".tar.gz"):

            match_object = re.search(config_manager.config_data["image-archive-pattern"], archive_element)
            if match_object is not None:

                # extracting information from the image archive file name
                archive_timestamp = time.mktime(datetime.datetime.strptime(match_object.group(3), '%Y-%m-%d_%H-%M-%S').timetuple())
                archive_component_name = match_object.group(2)

                # checking if image name is related to the provided Node id
                id_pattern = archive_element.split(archive_component_name)[0][:-1]
                if re.match(id_pattern, node_id) is not None:
                    
                    # making sure the most recent images are selected
                    if archive_component_name in matched_image_files:
                        if archive_timestamp > matched_image_files[archive_component_name][0]:
                            matched_image_files[archive_component_name] = (archive_timestamp, archive_element)
                    else:
                        matched_image_files[archive_component_name] = (archive_timestamp, archive_element)

    # returning list of most recent relevant image archive file names
    return [matched_image_files[component_name][1] 
            for component_name in matched_image_files.keys()]