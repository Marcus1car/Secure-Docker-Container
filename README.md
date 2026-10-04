# Secure Docker Container for File Analysis & Execution  

[![CI](https://github.com/Marcus1car/Secure-Docker-Container/actions/workflows/ci.yml/badge.svg)](https://github.com/Marcus1car/Secure-Docker-Container/actions/workflows/ci.yml)




A secure, isolated environment for analyzing and executing potentially malicious files with strict resource controls.

## Key Features 🔒
- **YARA-Based Analysis**: Comprehensive file scanning using custom YARA rules
- **Safe Execution Sandbox**: 
  - Resource limits (CPU/Memory/Processes)
  - Time-constrained execution
  - Network isolation
  - Filesystem restrictions
- **Whitelisting System**: MIME-type based classification — a non-whitelisted type raises the reported threat level; it does not yet block execution
- **Comprehensive Logging**: Detailed execution and analysis records
- **Security Hardened**: Non-root execution, kernel hardening
- **Network Isolation** :     
  - All executions run with `network_mode: none`    
  - No inbound/outbound connections allowed

## File Structure 🏗 
```
.
├── Dockerfile
├── Dockerfile.test
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
├── requirements-dev.txt
├── config/
│ ├── execution_limits.json
│ └── whitelist.json
├── scripts/
│ ├── analyze.py
│ └── execute.py
├── yara-rules/
│ └── index.yar
├── samples/
└── tests/
```

## Quick Start 

**1. Build your container**     
```
mkdir -p logs 
sudo chown -R 10001:10001 logs
sudo chmod -R 775 logs
docker compose build
```    

**2. Static  File Analysis**     
```bash
docker compose run --rm analyze python3 analyze.py samples/dummy.pe
```

**3. Execute a File Safely**      
```bash
docker compose run --rm execute python3 execute.py samples/safe_script.sh
```

**Run the tests**
```bash
docker compose build secure-container
docker compose --profile test build test
docker compose --profile test run --rm test
./tests/smoke_entrypoints.sh
```

## Configuration and Usage 🔧 
**Execution Limits**      
Edit `config/execution_limits.json` to adjust resource constraints.
By default :
```json
{
  "memory_limit": 67108864,    // 64MB
  "cpu_time_limit": 30,        // CPU seconds
  "file_size_limit": 10485760, // 10MB
  "process_limit": 5,          // Max concurrent processes
  "max_execution_time": 5      // Wall-clock seconds
}
```

Run with custom limits config : 
```bash
docker compose run --rm \
  -v ./custom_config:/app/Secure-Docker-Container/config \
  execute python3 execute.py samples/safe_script.sh
```

**File Whitelisting**     
Edit `config/whitelist.json` to define allowed file types.
```json
{
  "allowed_mime_types": [
    "text/plain",
    "application/pdf",
    "image/jpeg"
  ]
}
```
Run with custom whitelist : 
```bash
docker compose run --rm \
  -v ./custom_whitelist.json:/app/Secure-Docker-Container/config/whitelist.json \
  analyze python3 analyze.py samples/clean.txt
```
**YARA Rules**      
Edit the YARA rules in `yara-rules/` or mount custom rules:
```bash
docker compose run --rm \
  -v ./custom_rules:/app/yara-rules \
  analyze python3 analyze.py samples/dummy.pe
```
**Log Inspection**      
View execution and analysis logs:    
```bash
docker compose run --rm analyze cat /app/Secure-Docker-Container/logs/execution.log
```

```bash
docker compose run --rm analyze cat /app/Secure-Docker-Container/logs/file_analysis.log
```
 
