#!/bin/bash
# Deployment script for the Tremium Hub
# This script needs root privileges to properly execute
#
# Usage: 
#   ./hub-setup.sh 0 (if Docker engine is already installed on the machine)
#   ./hub-setup.sh 1 (if Docker engine needs to be installed on the machine)
# -----------------------------------------------------------------------------

# defining tremium hub user (taget for configuration)
tremium_user="david"

# defining necessary docker parameters
image_registry_host="https://gcr.io"
registry_credentials_path="/home/david/Documents/Tremium/tremium-hub/Config/TremiumDevEditor.json"

# defining the installation policy
install_docker_engine=$1

# setting up docker on the host machine
if [ "$install_docker_engine" -eq 1 ] 
    then 
        echo -e "\nInstalling Docker engine ... \n"
        sh ./get-docker.sh
        systemctl start docker
fi

# logging in to the docker registry
echo -e "\nLogging in to the Tremium image registry ... \n"
cat $registry_credentials_path | docker login -u _json_key --password-stdin $image_registry_host

# launching the ouroboros service
echo -e "\nLaunching the ouroboros update service ... \n"
docker run -d --name ouroboros \
  -v /var/run/docker.sock:/var/run/docker.sock \
  pyouroboros/ouroboros

# giving proper rights to the tremium user (docker)
echo -e "\nGiving proper rights to the tremium user (docker)... \n"
usermod -aG docker $tremium_user
chown "$tremium_user":"$tremium_user" /home/"$tremium_user"/.docker -R
chmod g+rwx "/home/$tremium_user/.docker" -R

# defining environment variables for GCP
echo -e "\nDefining environment variables for GCP in .bashrc... \n"
echo "export GOOGLE_APPLICATION_CREDENTIALS=$registry_credentials_path" >> /home/"$tremium_user"/.bashrc
source /home/"$tremium_user"/.bashrc

echo -e "\nClose current shell window and login as the specified tremium user \n"