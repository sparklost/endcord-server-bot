#!/usr/bin/env bash

set -e

if [[ "${1:-}" == "--stop" ]]; then
    pkill sshd
    pkill tor
else
    sshd
    tor > /dev/null 2>&1 &

    ONION=$(cat ~/.tor/torssh/hostname)
    echo "Address: \`$ONION\`"
    echo "Port: \`22\`"
    echo "Username: \`$USER\`"
fi

