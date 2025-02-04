cp of old dockerfile 
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