# Working directory structure for image build
    # communication (dir)
    # tremium (dir)    
    # config (dir)
    # requirements.txt
    # Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.7

# set working directory + copy necessary sources and folders
WORKDIR /tremium-hub
COPY ./tremium /tremium_hub
COPY ./requirements.txt /tremium_hub
COPY ./config/hub-config.json /tremium_hub
COPY ./communication/update-manager/update-manager.py /tremium_hub
COPY ./communication/data-collector/data-collector.py /tremium_hub
COPY ./communication/data-collector/launch-data-collector.sh /tremium_hub
COPY ./communication/iot-communication-interface/bluetooth-interface.py /tremium_hub

# creating necessary empty directories
RUN mkdir file-transfer-hub
RUN mkdir image-archives-hub