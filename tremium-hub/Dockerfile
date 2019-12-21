# Use an official Python runtime as a parent image
FROM python:3.6.8

# set working directory + copy necessary sources and folders
WORKDIR /tremium-hub
COPY ./* /tremium-hub/

# creating necessary empty directories
RUN mkdir file-transfer-hub
RUN mkdir image-archives-hub

# installing os dependencies
RUN apt-get update
RUN apt-get -y install cron
RUN apt-get -y install usbutils bluez bluetooth libbluetooth-dev python-dev

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
RUN crontab /etc/cron.d/data-collector-cron

# testing (running something in the back ground)
CMD tail -f /dev/null