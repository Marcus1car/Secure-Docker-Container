# Use a lightweight base image
FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Create directory structure
RUN mkdir -p \
    /app/Secure-Docker-Container/logs \
    /app/Secure-Docker-Container/samples \
    /app/Secure-Docker-Container/scripts \
    /var/run/clamav \
    /var/log/clamav

# Set workdir for subsequent commands
WORKDIR /app/Secure-Docker-Container/scripts

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-minimal \
    python3-pip \
    libmagic1 \
    clamav \
    clamav-daemon \
    gosu \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configure ClamAV
RUN echo "LocalSocket /var/run/clamav/clamd.sock" >> /etc/clamav/clamd.conf && \
    echo "User fileanalyst" >> /etc/clamav/clamd.conf && \
    echo "LogFile /var/log/clamav/clamd.log" >> /etc/clamav/clamd.conf && \
    echo "LogTime yes" >> /etc/clamav/clamd.conf && \
    echo "MaxFileSize 100M" >> /etc/clamav/clamd.conf && \
    echo "MaxScanSize 100M" >> /etc/clamav/clamd.conf && \
    echo "StreamMaxLength 100M" >> /etc/clamav/clamd.conf

RUN echo "Debug yes" >> /etc/clamav/clamd.conf && \
    echo "Foreground yes" >> /etc/clamav/clamd.conf
    
# Copy application files FIRST
COPY scripts/analyze.py scripts/execute.py .

# Create non-root user and set ownership
RUN groupadd -g 10001 fileanalyst && \
    useradd -u 10001 -g fileanalyst -s /bin/bash -m -d /home/fileanalyst fileanalyst && \
    chown -R fileanalyst:fileanalyst \
        /app/Secure-Docker-Container \
        /var/run/clamav \
        /var/log/clamav

# Set file permissions AFTER ownership change
RUN chmod 750 *.py && \
    chmod 770 /app/Secure-Docker-Container/logs

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy and prepare entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Security hardening
RUN echo "kernel.unprivileged_userns_clone=0" >> /etc/sysctl.d/10-security.conf && \
    echo "kernel.core_pattern=|/bin/false" >> /etc/sysctl.d/10-security.conf

# Final container configuration
USER fileanalyst
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "analyze.py"]