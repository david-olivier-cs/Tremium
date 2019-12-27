#!/bin/bash
# Jenkins build script for the "tremium-hub" (free style project)
# This script gets called once the "Tremium" repo is cloned to the build directory
# This script is launched from "Tremium/tremium-hub"
#
# Usage:
# cd ./tremium-hub && chmod 777 jenkins-build.sh && ./jenkins-build.sh

# defining the build directory name
build_folder="tremium-hub-build"

# creating the build directory and copying copying dependencies
rm -fr $build_folder && mkdir $build_folder
cp ./Dockerfile ./$build_folder/
cp ./requirements.txt ./$build_folder/
cp ./launch-hub-services.sh ./$build_folder/
cp -r ../tremium-py/ ./$build_folder/
cp ./config/hub-config.json ./$build_folder/
cp ./config/TremiumDevEditor.json ./$build_folder/
cp ./communication/update-manager/update-manager.py ./$build_folder/
cp ./communication/data-collector/data-collector.py ./$build_folder/
cp ./communication/data-collector/data-collector-cron ./$build_folder/
cp ./communication/data-collector/launch-data-collector.sh ./$build_folder/
cp ./communication/iot-communication-interface/bluetooth-interface.py ./$build_folder/

# moving into the build folder
cd $build_folder

# logging in to google docker registry
cat TremiumDevEditor.json | docker login -u _json_key --password-stdin https://gcr.io

# launching the docker image build
docker build . -t gcr.io/tremium/tremium_hub_container:latest

# pushing the docker image to the cloud registry
docker push gcr.io/tremium/tremium_hub_container:latest