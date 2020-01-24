#!/bin/bash
# Setup script for the Tremium Node host device
#
# Requirements
#   Needs internet access
#   Needs root privileges to properly execute
#   Needs the google cloud credentials .json file
#   Needs to be next to the get-docker.sh
# Usage: 
#   ./hub-setup.sh (credentials .json file path)
# -----------------------------------------------------------------------------

# fetching script arguments
registry_credentials_path=$1

# general configuration
tremium_user="one_wizard_boi"
image_registry_host="https://gcr.io"

echo -e "\nRunning setup script for deployment ... \n"

# creating the folders for volume mounting
mkdir $HOME/tremium-mounted-volumes
mkdir $HOME/tremium-mounted-volumes/image-archives-node
mkdir $HOME/tremium-mounted-volumes/file-transfer-node

# creating update entry file
touch $HOME/tremium-mounted-volumes/image-archives-node/node-image-updates.txt

# placing the "launch-node-container.sh" script
cp ./launch-node-container.sh $HOME/launch-node-container.sh
chmod 777 $HOME/launch-node-container.sh

# placing the node update script
cp ./update-node.sh $HOME/update-node.sh 
chmod 777 $HOME/update-node.sh

# installing os dependencies
apt-get update
apt-get -y install cron 
apt-get -y install redis-server libasound-dev portaudio19-dev libportaudio2 libportaudiocpp0
apt-get -y install usbutils bluez bluetooth libbluetooth-dev

# making necessary changes to the bluetooth interface
config_file="/etc/systemd/system/dbus-org.bluez.service"
target_line="ExecStart=/usr/lib/bluetooth/bluetoothd"
replacement_line="ExecStart=/usr/lib/bluetooth/bluetoothd -C"
sed -i 's/"$target_line"/"$replacement_line"/g' $config_file
systemctl daemon-reload
service bluetooth restart

# setting up redis
sudo systemctl enable redis-server.service

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
docker pull gcr.io/tremium/dev_node_testing_01_acquisition-component:latest

# scheduling the node start up script on host device power up
# setting update checks every 5 minutes
crontab -l > new_cron
echo "@reboot $HOME/launch-node-container.sh" >> new_cron
echo "*/5 * * * * $HOME/update-node.sh $HOME/tremium-mounted-volumes/image-archives-node/node-image-updates.txt" >> new_cron
crontab new_cron
rm new_cron

# restarting the host device
echo -e "\nTremium Node will be launched after reboot \n"
reboot