#!/usr/bin/env bash

PROJECT_ROOT="$HOME/endcord"
PID_FILE=".endcord.pid"

ACTIONS=()

# argparser
while [[ $# -gt 0 ]]; do
    case "$1" in
        start|stop|update)
            ACTIONS+=("$1")
            ;;
        restart)
            ACTIONS+=("stop" "start")
            ;;
        restart-update)
            ACTIONS+=("stop" "update" "start")
            ;;
        *)
            if [[ ${#ACTIONS[@]} -eq 0 ]]; then
                PROJECT_ROOT="$1"
            else
                echo "Unknown argument: $1"
                echo "Usage: $0 [project_root] {start|stop|update|restart|restart-update}"
                exit 1
            fi
            ;;
    esac
    shift
done

# usage
if [[ ${#ACTIONS[@]} -eq 0 ]]; then
    echo "Usage: $0 [project_root] {start|stop|update|restart|restart-update}"
    exit 1
fi

# cd to project root
if ! cd "$PROJECT_ROOT" >/dev/null 2>&1; then
    echo "Error: Cannot find project root at '$PROJECT_ROOT'"
    exit 1
fi

# actions
do_start() {
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Endcord is already running (PID: $(cat "$PID_FILE"))."
        return
    fi
    nohup uv run main.py --headless > /dev/null 2>&1 &
    PID=$!
    echo "$PID" > "$PID_FILE"
    echo "Endcord started (PID: $PID)"
}

do_stop() {
    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Stopping endcord (PID: $PID)..."
            kill -2 "$PID"
            for _ in {1..3}; do
                if kill -0 "$PID" 2>/dev/null; then
                    sleep 1
                else
                    break
                fi
            done
            if kill -0 "$PID" 2>/dev/null; then
                echo "Endcord did not stop gracefully. Forcing kill..."
                kill -9 "$PID" 2>/dev/null
            fi
        fi
        rm -f "$PID_FILE"
    else
        echo "Endcord is not running"
    fi
}

do_update() {
    echo "Updating endcord..."
    git fetch origin
    git reset --hard origin/main
    uv remove numpy soundcard soundfile orjson pycryptodome psutil || true
}

# execute queued actions
for action in "${ACTIONS[@]}"; do
    case "$action" in
        start) do_start ;;
        stop) do_stop ;;
        update) do_update ;;
    esac
done
