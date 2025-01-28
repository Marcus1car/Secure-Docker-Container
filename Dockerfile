# Use a lightweight base image
FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Create directory structure first
RUN mkdir -p /app/Secure-Docker-Container/logs && \
    mkdir -p /app/Secure-Docker-Container/samples && \
    mkdir -p /app/Secure-Docker-Container/scripts

# Set workdir
WORKDIR /app/Secure-Docker-Container

# Install essential security and analysis tools
RUN apt-get update && apt-get install -y \
    python3-minimal \
    python3-pip \
    python3-magic \
    clamav \
    firejail \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Update ClamAV virus definitions
RUN freshclam

# Create non-root user with specific UID/GID
RUN groupadd -g 10001 fileanalyst && \
    useradd -u 10001 -g fileanalyst -s /bin/bash -m -d /home/fileanalyst fileanalyst

# Copy and install requirements first (for better layer caching)
COPY requirements.txt /app/Secure-Docker-Container/
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files with correct paths
COPY scripts/analyze.py scripts/execute.py /app/Secure-Docker-Container/scripts/

# Set proper permissions
RUN chown -R fileanalyst:fileanalyst /app/Secure-Docker-Container && \
    chmod -R 750 /app/Secure-Docker-Container && \
    chmod 770 /app/Secure-Docker-Container/logs && \
    chmod 750 /app/Secure-Docker-Container/samples && \
    chmod 500 /app/Secure-Docker-Container/scripts/*.py

# Add security configurations
RUN echo "noroot" >> /etc/firejail/firejail.config && \
    echo "force-nonewprivs" >> /etc/firejail/firejail.config && \
    echo "ignore private-dev" >> /etc/firejail/firejail.config && \
    echo "ignore private-tmp" >> /etc/firejail/firejail.config

# Add ClamAV security configurations
RUN echo "MaxFileSize 100M" >> /etc/clamav/clamd.conf && \
    echo "MaxScanSize 100M" >> /etc/clamav/clamd.conf && \
    echo "StreamMaxLength 100M" >> /etc/clamav/clamd.conf

# Add system security configurations
RUN echo "kernel.unprivileged_userns_clone=0" >> /etc/sysctl.d/10-security.conf && \
    echo "kernel.core_pattern=|/bin/false" >> /etc/sysctl.d/10-security.conf

# Switch to non-root user
USER fileanalyst

# Set secure workdir
WORKDIR /app/Secure-Docker-Container/scripts

# Health check
HEALTHCHECK --interval=5m --timeout=3s \
    CMD pgrep clamd || exit 1

# Default command
CMD ["/usr/bin/python3", "analyze.py"]