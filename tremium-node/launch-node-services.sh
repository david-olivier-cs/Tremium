#!/bin/bash
# Entry point for services running inside the "tremium-hub" docker container

# launching the maintenance service (in background)
maintenance_cmd="python maintenance.py $TREMIUM_CONFIG_FILE"
$maintenance_cmd &

# launching cron
cron

# preventing the docker "CMD" from ending
tail -f /dev/null