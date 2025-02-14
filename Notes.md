*cp of old dockerfile*
```
# Use a lightweight base image
FROM ubuntu:22.04


# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Set workdir
WORKDIR /app

# Install essential security and analysis tools
RUN apt-get update && apt-get install -y \  
    python3 \
    python3-pip \
    clamav \
    firejail \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*



# Update ClamAV virus definitions
RUN freshclam

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy scripts
COPY scripts/analyze.py .
COPY scripts/execute.py .

# Additional security hardening
RUN adduser --disabled-password --gecos '' fileanalyst \
    && chown -R fileanalyst:fileanalyst /app

# Create a non-root user for enhanced security
RUN useradd -m fileanalyst
USER fileanalyst

# Default command (can be overridden)
CMD ["/bin/bash"]
```



```
docker run --rm \
  -v $(pwd)/logs:/app/Secure-Docker-Container/logs \
  -v $(pwd)/samples:/app/Secure-Docker-Container/samples:ro \
  secure-container python3 analyze.py /app/Secure-Docker-Container/samples/safe.txt
```

```
docker run --rm \
  -v $(pwd)/logs:/app/Secure-Docker-Container/logs \
  -v $(pwd)/samples:/app/Secure-Docker-Container/samples:ro \
  secure-container python3 scripts/analyze.py samples/safe.txt
```


alright done now i need to test it , can you give me test files , their respective expected output and the command to dot it



**Ensured ClamAV configuration is properly set with minimal duplication. in the Dockerfile**

**freshclam should run as fileanalyst instead of root in entrypoint.sh**





*old entrypoint*`
```
#!/bin/sh
set -ex

if [ "$(id -u)" = "0" ]; then
  # Update virus databases first
  echo "Updating definitions..."
  freshclam

  # Start ClamAV daemon in background
  echo "Starting ClamAV..."
  clamd &

  # Wait for socket creation with timeout
  echo "Waiting for socket..."
  timeout=10
  while [ ! -S /var/run/clamav/clamd.sock ] && [ $timeout -gt 0 ]; do
    sleep 1
    ((timeout--))
  done

  if [ ! -S /var/run/clamav/clamd.sock ]; then
    echo "ERROR: ClamAV socket not created after 10 seconds!"
    exit 1
  fi

  # Set permissions
  chown fileanalyst:fileanalyst /var/run/clamav/clamd.sock
  chmod 660 /var/run/clamav/clamd.sock

  # Drop privileges and execute command
  exec gosu fileanalyst "$@"
fi

exec "$@"
```