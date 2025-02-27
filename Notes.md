*cp of old dockerfile*
```
# Use a lightweight base image
FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Create directory structure
RUN mkdir -p \
    /app/Secure-Docker-Container/logs \
    /app/Secure-Docker-Container/samples \
    /app/Secure-Docker-Container/scripts \
    /app/yara-rules

# Set workdir for subsequent commands
WORKDIR /app/Secure-Docker-Container/scripts


# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-minimal \
    python3-pip \
    libmagic1 \
    yara\
    gosu \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*



# Create non-root user and set ownership
RUN groupadd -g 10001 fileanalyst && \
    useradd -u 10001 -g fileanalyst -s /bin/bash -m -d /home/fileanalyst fileanalyst && \
    chown -R fileanalyst:fileanalyst /app/Secure-Docker-Container /app/yara-rules

COPY --chown=fileanalyst:fileanalyst scripts/analyze.py scripts/execute.py .
COPY yara-rules /app/yara-rules

# Set file permissions AFTER ownership change
RUN chmod 750 *.py && \
    chmod 770 /app/Secure-Docker-Container/logs

RUN chmod 755 /app /app/Secure-Docker-Container && \
    chmod 755 /app/Secure-Docker-Container/scripts

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






***COMMAND***

docker build -t file-analyzer .

docker run -v "$(pwd)/yara-rules:/app/yara-rules" \
           -v "$(pwd)/samples:/app/Secure-Docker-Container/samples" \
           -v "$(pwd)/logs:/app/Secure-Docker-Container/logs" \
           file-analyzer python3 analyze.py /app/Secure-Docker-Container/samples/clean.txt








***COPY OF ANALYSIS.PY***

import os
import sys
import logging
import magic
import yara
import json
from typing import Dict, Any
from pathlib import Path


class FileAnalyzer:
    def __init__(self, log_path: str = '/app/Secure-Docker-Container/logs/file_analysis.log'):
        
        
        
        
        
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=log_path,
            filemode='a'  # Append mode to allow multiple script logs
        )
        self.logger = logging.getLogger(__name__)
        self.yara_rules = self._load_yara_rules()
        self.whitelist = self._load_whitelist()

    def _load_whitelist(self) -> list:
        config_path = Path('/app/Secure-Docker-Container/config/whitelist.json')
        try:
            with open(config_path) as f:
                return json.load(f)['allowed_mime_types']
        except Exception as e:
            self.logger.error(f"Whitelist loading error: {e}")
            return []
    
    
    def get_file_type(self, file_path: str) -> str:
        """
        Detect file type using python-magic.
        """
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path)
        except Exception as e:
            self.logger.error(f"File type detection error: {e}")
            return "Unknown"

    def _load_yara_rules(self):
        try:
            # Load all YARA rules from directory
            rules = yara.compile('/app/yara-rules/index.yar')
            self.logger.info("YARA rules loaded successfully")
            return rules
        except yara.Error as e:
            self.logger.error(f"YARA rule loading error: {e}")
            return None

    def scan_with_yara(self, file_path: str) -> dict:
        """
        Scan the file with YARA rules
        """
        if not self.yara_rules:
            return {"error": "YARA rules not loaded"}
            
        try:
            matches = self.yara_rules.match(file_path)
            return {
                "malicious": len(matches) > 0,
                "matches": [str(m) for m in matches]
            }
        except Exception as e:
            self.logger.error(f"YARA scan error: {e}")
            return {"error": str(e)}

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Perform a comprehensive analysis of the file.
        """
        # Validate file existence
        if not os.path.isfile(file_path):
            self.logger.error(f"File not found: {file_path}")
            return {"error": "File not found"}
        
        file_type = self.get_file_type(file_path)
        is_whitelisted = file_type in self.whitelist

        
        # Gather file details
        analysis_result = {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "file_type": self.get_file_type(file_path),
            "whitelist_status": "allowed" if is_whitelisted else "blocked",
            "yara_result": self.scan_with_yara(file_path)
        }
        
        analysis_result["threat_level"] = self._assess_threat(analysis_result)
        # Log the analysis result
        self.logger.info(f"File analyzed: {json.dumps(analysis_result, indent=2)}")

        return analysis_result

    def _assess_threat(self, result: dict) -> str:
        if result["whitelist_status"] == "blocked":
            return "high"
        if result["yara_result"]["malicious"]:
            return "medium"
        return "low"


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <file_path>")
        sys.exit(1)

    analyzer = FileAnalyzer()
    result = analyzer.analyze_file(sys.argv[1])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
