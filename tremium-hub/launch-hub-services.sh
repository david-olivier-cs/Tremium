#!/bin/bash
# Entry point for services running inside the "tremium-hub" docker container

# launching the bluetooth server (in background)
bluetooth_cmd="python bluetooth-interface.py $TREMIUM_CONFIG_FILE"
$bluetooth_cmd &

# launching the update manager (in background)
update_manager_cmd="python update-manager.py $TREMIUM_CONFIG_FILE"
$update_manager_cmd &

# launching cron
cron

# preventing the docker "CMD" from ending
tail -f /dev/null