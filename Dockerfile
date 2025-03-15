# Use a lightweight base image
FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Create directory structure
RUN mkdir -p \
    /app/Secure-Docker-Container/logs \
    /app/Secure-Docker-Container/samples \
    /app/Secure-Docker-Container/scripts \
    /app/Secure-Docker-Container/config \
    /app/yara-rules

# Set workdir for subsequent commands
WORKDIR /app/Secure-Docker-Container 



# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-minimal \
    python3-pip \
    libmagic1 \
    yara \
    gosu \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and set ownership
RUN groupadd -g 10001 fileanalyst && \
    useradd -u 10001 -g fileanalyst -s /bin/bash -m -d /home/fileanalyst fileanalyst && \
    chown -R fileanalyst:fileanalyst /app/Secure-Docker-Container /app/yara-rules && \ 
    chown -R fileanalyst:fileanalyst /app/Secure-Docker-Container/logs

# Copy application files with correct ownership
COPY --chown=fileanalyst:fileanalyst scripts/analyze.py scripts/execute.py .
COPY --chown=fileanalyst:fileanalyst yara-rules /app/yara-rules
COPY --chown=fileanalyst:fileanalyst config/whitelist.json /app/Secure-Docker-Container/config/

# Set directory permissions
RUN chmod 755 /app /app/Secure-Docker-Container && \
    chmod 755 /app/Secure-Docker-Container/scripts && \
    chmod 750 *.py && \
    chmod 775 /app/Secure-Docker-Container/logs


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