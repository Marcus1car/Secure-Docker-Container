# Secure Docker Container for File Analysis & Execution  

![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![YARA](https://img.shields.io/badge/YARA-220000?style=for-the-badge)

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

## Architecture 🏗 
```
.
├── Dockerfile
├── docker-compose.yml
├── config/
│ ├── execution_limits.json
│ └── whitelist.json
├── scripts/
│ ├── analyze.py
│ └── execute.py
├── yara-rules/
│ └── custom_rules.yar
└── samples/
```

## Quick Start 

**1. Build your container**     
`docker-compose build`     

**2. Static  File Analysis**     
`docker-compose run --rm analyze python3 analyze.py samples/suspicious_file`     

**3. Execute a File Safely**      
`docker-compose run --rm execute python3 execute.py samples/test_script.sh`

## Configuration and Usage 🔧 
**Execution Limits** 
Edit `config/execution_limits.json` to adjust resource constraints.
By default :
```
{
  "memory_limit": 67108864,    // 64MB
  "cpu_time_limit": 30,        // CPU seconds
  "file_size_limit": 10485760, // 10MB
  "process_limit": 5,          // Max concurrent processes
  "max_execution_time": 5      // Wall-clock seconds
}
```

Run with custom limits config : 
```
docker-compose run --rm execute \
  -v ./custom_config:/app/Secure-Docker-Container/config \
  python3 execute.py samples/script.sh
```

**File Whitelisting**     

Edit `config/whitelist.json` to define allowed file types.
```
{
  "allowed_mime_types": [
    "text/plain",
    "application/pdf",
    "image/jpeg"
  ]
}
```
Run with custom whitelist : 
```
docker-compose run --rm analyze \
  -v ./custom_whitelist.json:/app/Secure-Docker-Container/config/whitelist.json \
  python3 analyze.py samples/document.pdf
```

