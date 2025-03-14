# Secure Docker Container for File Analysis & Execution  

![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![YARA](https://img.shields.io/badge/YARA-220000?style=for-the-badge)



**Project Overview :**  
A secure, isolated environment for analyzing and executing potentially malicious files with strict resource controls.


## Key Features 🔒
- **YARA-Based Analysis**: Comprehensive file scanning using custom YARA rules
- **Safe Execution Sandbox**: 
  - Resource limits (CPU/Memory/Processes)
  - Time-constrained execution
  - Network isolation
  - Filesystem restrictions
- **Whitelisting System**: MIME-type based file approval
- **Comprehensive Logging**: Detailed execution and analysis records
- **Security Hardened**: Non-root execution, kernel hardening


Project for cybersecurity researchers, malware analysts, and security professionals who need a controlled, isolated space to examine potentially harmful software.
Architectural Components :


**DockerFile :**
```
Using a lightweight Ubuntu base image
Creating a virtual environment
Installing minimal necessary tools
```

**Python Script :**

  ```
  analyze.py : Analyze given file using ClamAV
  Execute.py : Safely execute a file with strict controls / LOGGING
  ```
        
        Key Safety Features:
        - Unique execution context for each file
        - Time-limited execution
        - Resource constraints
        - Isolated environment



**Run commands**

`docker build -t file-analyzer .`  
`docker run -v "$(pwd)/samples:/app/Secure-Docker-Container/samples" file-analyzer python3 analyze.py /path/to/sample`
