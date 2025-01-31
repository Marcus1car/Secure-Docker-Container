# Use a lightweight base image
FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Create directory structure
RUN mkdir -p /app/Secure-Docker-Container/logs && \
    mkdir -p /app/Secure-Docker-Container/samples && \
    mkdir -p /app/Secure-Docker-Container/scripts

# Set workdir
WORKDIR /app/Secure-Docker-Container

# Install essential packages
RUN apt-get update && apt-get install -y \
    python3-minimal \
    python3-pip \
    libmagic1 \
    clamav \
    clamav-daemon \
    gosu \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configure ClamAV
RUN echo "LocalSocket /tmp/clamd.sock" >> /etc/clamav/clamd.conf && \
    echo "MaxFileSize 100M" >> /etc/clamav/clamd.conf && \
    echo "MaxScanSize 100M" >> /etc/clamav/clamd.conf && \
    echo "StreamMaxLength 100M" >> /etc/clamav/clamd.conf

# Create non-root user
RUN groupadd -g 10001 fileanalyst && \
    useradd -u 10001 -g fileanalyst -s /bin/bash -m -d /home/fileanalyst fileanalyst

# Install Python dependencies
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY scripts/analyze.py scripts/execute.py ./scripts/

# Set permissions
RUN chown -R fileanalyst:fileanalyst /app/Secure-Docker-Container && \
    chmod -R 750 /app/Secure-Docker-Container && \
    chmod 770 logs && \
    chmod 500 scripts/*.py

# Add entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Security configurations
RUN echo "kernel.unprivileged_userns_clone=0" >> /etc/sysctl.d/10-security.conf && \
    echo "kernel.core_pattern=|/bin/false" >> /etc/sysctl.d/10-security.conf

# Final setup
USER fileanalyst
WORKDIR /app/Secure-Docker-Container/scripts

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "analyze.py"]