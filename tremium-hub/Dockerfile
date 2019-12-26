# Use an official Python runtime as a parent image
FROM python:3.6.8

# set working directory + copy necessary sources and folders
WORKDIR /tremium-hub
COPY ./* /tremium-hub/

# installing os dependencies
RUN apt-get update
RUN apt-get -y install cron
RUN apt-get -y install usbutils bluez bluetooth libbluetooth-dev python-dev

# installing docker
RUN apt-get -y install lsb-release apt-transport-https ca-certificates curl gnupg2 software-properties-common
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
RUN add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"
RUN apt-get update
RUN apt-get -y install docker-ce docker-ce-cli containerd.io

# installing python packages
RUN pip install -r ./requirements.txt
RUN pip install ./tremium
RUN rm ./requirements.txt

# defining environment variables
ENV TREMIUM_MAIN_DIR /tremium-hub
ENV TREMIUM_CONFIG_FILE /tremium-hub/hub-config.json
ENV GOOGLE_APPLICATION_CREDENTIALS /tremium-hub/TremiumDevEditor.json

# setting up the data-collector cronjob
COPY data-collector-cron /etc/cron.d/data-collector-cron
RUN chmod 0644 /etc/cron.d/data-collector-cron
RUN chmod 777 /tremium-hub/launch-data-collector.sh
RUN crontab /etc/cron.d/data-collector-cron

# creating necessary empty directories
RUN mkdir file-transfer-hub
RUN mkdir image-archives-hub

# testing (running something in the back ground)
CMD ./launch-hub-services.sh