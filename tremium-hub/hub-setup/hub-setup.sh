#!/bin/bash
# Setup script for the Tremium Hub host device
#
# Requirements
#   Needs internet access
#   Needs root privileges to properly execute
#   Needs the google cloud credentials .json file
#   Needs to be next to the get-docker.sh
# Usage: 
#   ./hub-setup.sh (credentials .json file path) 1 --> setup for test
#   ./hub-setup.sh (credentials .json file path) 0 --> setup for deployment
# -----------------------------------------------------------------------------

# fetching script arguments
registry_credentials_path=$1
run_context=$2

# general configuration
tremium_user="one_wizard_boi"
image_registry_host="https://gcr.io"

# running the script according to the context
if [ "$run_context" -eq 1 ]
  
    # setting up with a test context
    then

        echo -e "\nRunning setup script for testing ... \n"

        # defining test configurations
        tremium_main_dir="/home/one_wizard_boi/Documents/Projects/Tremium/Tremium"
        tremium_config_file="/home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/config/hub-test-config.json"
        registry_credentials_path="/home/one_wizard_boi/Documents/Projects/Tremium/Tremium/tremium-hub/config/TremiumDevEditor.json"

        # defining environment variables for GCP
        echo -e "\nDefining environment variables for GCP in .bashrc... \n"
        echo "export GOOGLE_APPLICATION_CREDENTIALS=$registry_credentials_path" >> /home/"$tremium_user"/.profile
        echo "export GOOGLE_APPLICATION_CREDENTIALS=$registry_credentials_path" >> /home/"$tremium_user"/.bashrc

        # defining environment variables for tremium
        echo "export TREMIUM_MAIN_DIR=$tremium_main_dir" >> /home/"$tremium_user"/.profile
        echo "export TREMIUM_MAIN_DIR=$tremium_main_dir" >> /home/"$tremium_user"/.bashrc
        echo "export TREMIUM_CONFIG_FILE=$tremium_config_file" >> /home/"$tremium_user"/.profile
        echo "export TREMIUM_CONFIG_FILE=$tremium_config_file" >> /home/"$tremium_user"/.bashrc

        # applying .profile configurations
        source /home/"$tremium_user"/.bashrc

    # setting up with a deployment context
    else

        echo -e "\nRunning setup script for deployment ... \n"

        # creating the folders for volume mounting
        mkdir $HOME/tremium-mounted-volumes
        mkdir $HOME/tremium-mounted-volumes/image-archives-hub
        mkdir $HOME/tremium-mounted-volumes/file-transfer-hub

        # placing the "launch-hub-container.sh" script
        cp ./launch-hub-container.sh $HOME/launch-hub-container.sh
        chmod 777 $HOME/launch-hub-container.sh

fi

# installing os dependencies
apt-get update
apt-get -y install cron
apt-get -y install usbutils bluez bluetooth libbluetooth-dev

# making necessary changes to the bluetooth interface
config_file="/etc/systemd/system/dbus-org.bluez.service"
target_line="ExecStart=/usr/lib/bluetooth/bluetoothd"
replacement_line="ExecStart=/usr/lib/bluetooth/bluetoothd -C"
sed -i 's/"$target_line"/"$replacement_line"/g' $config_file
systemctl daemon-reload
service bluetooth restart

# installing docker, if not installed
docker_socket=/var/run/docker.sock
if test -e "$docker_socket"
    then
        echo -e "\nDocker already installed on host machine \n"
    else
        echo -e "\nInstalling Docker engine ... \n"
        sh ./get-docker.sh
        systemctl start docker

        echo -e "\nGiving proper rights to the tremium user (docker)... \n"
        usermod -a -G docker $tremium_user
        chown "$tremium_user":"$tremium_user" /home/"$tremium_user"/.docker -R
        chmod g+rwx "/home/$tremium_user/.docker" -R
fi

# logging in to the google docker registry
echo -e "\nLogging in to the Tremium image registry ... \n"
cat $registry_credentials_path | docker login -u _json_key --password-stdin $image_registry_host

# pulling the main hub image from the cloud registry
docker pull gcr.io/tremium/tremium_hub_container:latest

# scheduling the hub start up script on host device power up
crontab -l > new_cron
echo "@reboot $HOME/launch-hub-container.sh 0" >> new_cron
crontab new_cron
rm new_cron

# restarting the host device
echo -e "\nTremium Hub will be launched after reboot \n"
reboot