#!/bin/bash
# Launcher script for the data collector component
# This script is meant to be launched by a cron job "see hub-setup.sh"
#
# Usage : 
#   ./launch-data-collector.sh
# -----------------------------------------------------------------------------

# defining google authentification env variable
export GOOGLE_APPLICATION_CREDENTIALS=/tremium-hub/TremiumDevEditor.json

# launching the hub data collector
cd /tremium-hub
/usr/local/bin/python3.6 data-collector.py hub-config.json