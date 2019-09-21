#!/bin/bash
# Launcher script for the data collector component
# This script is meant to be launched by a cron job "see hub-setup.sh"
#
# Usage : 
#   ./launch-data-collector.sh
# -----------------------------------------------------------------------------

# sourcing the bash profile of the tremium user
source $HOME/.profile
        
# launching the hub data collector
cd $TREMIUM_MAIN_DIR
python3 data-collector.py $TREMIUM_CONFIG_FILE