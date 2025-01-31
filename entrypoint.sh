#!/bin/sh
set -e

# Start ClamAV daemon as root
if [ "$(id -u)" = "0" ]; then
    clamd &
    freshclam
    chmod 666 /tmp/clamd.sock
    exec gosu fileanalyst "$@"
else
    exec "$@"
fi