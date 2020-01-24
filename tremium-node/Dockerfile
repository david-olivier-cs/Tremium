# Use an official Python runtime as a parent image
FROM python:3.6.8

# set working directory + copy necessary sources and folders
WORKDIR /tremium-node
COPY ./* /tremium-node/

# installing os dependencies
RUN apt-get update
RUN apt-get -y install usbutils bluez bluetooth libbluetooth-dev python-dev
RUN apt-get install -y libasound-dev portaudio19-dev libportaudio2 libportaudiocpp0

# installing python packages
RUN pip install -r ./requirements.txt
RUN pip install ./tremium
RUN rm ./requirements.txt

# defining environment variables
ENV TREMIUM_MAIN_DIR /tremium-node
ENV TREMIUM_CONFIG_FILE /tremium-node/node-config.json

# creating necessary empty directories
RUN mkdir file-transfer-node
RUN mkdir image-archives-node

# launching entry point script
CMD ./launch-node-services.sh