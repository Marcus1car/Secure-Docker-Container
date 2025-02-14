#!/bin/sh
set -ex

if [ "$(id -u)" = "0" ]; then
  # Create directories and set permissions
  mkdir -p /var/run/clamav /var/log/clamav
  chown -R fileanalyst:fileanalyst /var/run/clamav /var/log/clamav
  chmod 770 /var/run/clamav /var/log/clamav

  # Update virus databases
  echo "Updating ClamAV definitions..."
  freshclam --user=fileanalyst --stdout

  # Start ClamAV daemon as non-root user
  echo "Starting ClamAV daemon..."
  gosu fileanalyst clamd -F --foreground &

  # Wait for socket creation with increased timeout
  echo "Waiting for socket..."
  timeout=20
  while [ ! -S /var/run/clamav/clamd.sock ] && [ $timeout -gt 0 ]; do
    sleep 1
    ((timeout--))
    echo "Waiting... $timeout seconds remaining"
  done

  if [ ! -S /var/run/clamav/clamd.sock ]; then
    echo "ERROR: ClamAV socket not created after 20 seconds!"
    exit 1
  fi

  # Verify socket permissions
  chown fileanalyst:fileanalyst /var/run/clamav/clamd.sock
  chmod 660 /var/run/clamav/clamd.sock

  # Drop privileges
  exec gosu fileanalyst "$@"
fi

exec "$@"