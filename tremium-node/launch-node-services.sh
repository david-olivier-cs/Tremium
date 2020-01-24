#!/bin/bash
# Entry point for services running inside the "tremium-hub" docker container

# launching the maintenance service (in background)
maintenance_cmd="python maintenance.py $TREMIUM_CONFIG_FILE"
$maintenance_cmd &

# launching audio recording and processing
audio_processing_cmd="python audio.py $TREMIUM_CONFIG_FILE"
$audio_processing_cmd &

# preventing the docker "CMD" from ending
tail -f /dev/null