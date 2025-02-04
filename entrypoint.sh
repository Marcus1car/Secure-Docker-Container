#!/bin/sh
set -ex

if [ "$(id -u)" = "0" ]; then
  # Update virus databases first
  echo "Updating definitions..."
  freshclam

  # Start ClamAV daemon as root
  echo "Starting ClamAV..."
  clamd

  # Wait for socket creation
  echo "Waiting for socket..."
  while [ ! -S /var/run/clamav/clamd.sock ]; do
    sleep 1
  done

  # Set permissions
  chown fileanalyst:fileanalyst /var/run/clamav/clamd.sock
  chmod 660 /var/run/clamav/clamd.sock

  # Drop privileges and execute command
  exec gosu fileanalyst "$@"
fi

exec "$@"