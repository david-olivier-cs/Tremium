#!/bin/bash
# Jenkins build script for the "tremium-node" (free style project)
# This script gets called once the "Tremium" repo is cloned to the build directory
# This script is launched from "Tremium/tremium-node"
#
# Usage:
# cd ./tremium-node && chmod 777 jenkins-build.sh && ./jenkins-build.sh

# defining the build directory name
build_folder="tremium-node-build"

# creating the build directory and copying copying dependencies
rm -fr $build_folder && mkdir $build_folder
cp ./Dockerfile ./$build_folder/
cp ./requirements.txt ./$build_folder/
cp ./launch-node-services.sh ./$build_folder/
cp -r ../tremium-py/ ./$build_folder/
cp ./config/node-config.json ./$build_folder/
cp ./maintenance/maintenance.py ./$build_folder/

# moving into the build folder
cd $build_folder

# logging in to google docker registry
cat TremiumDevEditor.json | docker login -u _json_key --password-stdin https://gcr.io

# launching the docker image build
docker build . -t gcr.io/tremium/dev_node_testing_01_acquisition-component:latest

# pushing the docker image to the cloud registry
docker push gcr.io/tremium/dev_node_testing_01_acquisition-component:latest