# Use an official Python runtime as a parent image
FROM python:3.6.8

# set working directory + copy necessary sources and folders
WORKDIR /tremium-node
COPY ./* /tremium-node/

# installing os dependencies
RUN apt-get update
RUN apt-get -y install cron
RUN apt-get -y install usbutils bluez bluetooth libbluetooth-dev python-dev

# installing python packages
RUN pip install -r ./requirements.txt
RUN pip install ./tremium
RUN rm ./requirements.txt

# defining environment variables
ENV TREMIUM_MAIN_DIR /tremium-node
ENV TREMIUM_CONFIG_FILE /tremium-hub/node-config.json

# creating necessary empty directories
RUN mkdir file-transfer-node
RUN mkdir image-archives-node

# setting up the update script cron job
COPY update-node-cron /etc/cron.d/update-node-cron
RUN chmod 0644 /etc/cron.d/update-node-cron
RUN chmod 777 /tremium-node/update-node.sh
RUN crontab /etc/cron.d/update-node-cron

# testing (running something in the back ground)
CMD ./launch-node-services.sh