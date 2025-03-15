import os
import sys
import subprocess
import resource
import time
import logging
import json
import signal
from typing import List, Optional , Any , Dict


def load_config(config_path='/app/Secure-Docker-Container/config/execution_limits.json') -> Dict[str, Any]:
    """
    Load resource limits from a configuration file.
    Falls back to default values if config file is not found or invalid.
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            if not all(isinstance(v, int) for v in config.values()):
                raise ValueError("Config values must be integers")
            return config
    
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        # Log error if needed
        print(f"Warning: Could not load config from {config_path}: {str(e)}")
        # Defaut Config
        return {
            "memory_limit": 64 * 1024 * 1024,       # 64MB
            "cpu_time_limit": 30,                   # 30 seconds CPU time
            "file_size_limit": 10 * 1024 * 1024,    # 10MB file size limit
            "process_limit": 5,                     # Max 5 processes
            "max_execution_time": 5                 # 5 seconds wall time
        }


class SafeExecutor:
    def __init__(self, 
                 log_dir: str = '/app/Secure-Docker-Container/logs', 
                 config_path: str = '/app/Secure-Docker-Container/config/execution_limits.json',
                 **override_params):
        """
        Initialize SafeExecutor with configurable execution parameters
        
        Args:
            log_dir: Directory for logs
            config_path: Path to the configuration file
            override_params: Parameters that override config file values
        """
        
        self.config = load_config(config_path)
        self.config.update(override_params)
        
        # Extract configuration values
        self.log_dir = os.path.abspath(log_dir)
        self.max_execution_time = self.config.get("max_execution_time", 5)
        self.memory_limit = self.config.get("memory_limit", 64 * 1024 * 1024)
        self.cpu_time_limit = self.config.get("cpu_time_limit")
        self.file_size_limit = self.config.get("file_size_limit", 1024 * 1024)
        self.process_limit = self.config.get("process_limit", 5)
        
       # Setup logging directory
        os.makedirs(self.log_dir, exist_ok=True)
        # Configure logging
        self.logger = logging.getLogger('SafeExecutor')
        self._setup_logging()
        self.logger.info(f"SafeExecutor initialized with config: {json.dumps(self.config, indent=2)}")

    def _setup_logging(self):
        """Configure logging with file rotation"""
        log_file = os.path.join(self.log_dir, 'execution.log')
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
        
    
    def _set_resource_limits(self):
        """Set resource limits for executed process based on configuration"""
        # Memory limit (RLIMIT_AS = address space limit)
        resource.setrlimit(resource.RLIMIT_AS, (self.memory_limit, self.memory_limit))
        # CPU time limit (seconds)
        if self.cpu_time_limit:
            resource.setrlimit(resource.RLIMIT_CPU, (self.cpu_time_limit, self.cpu_time_limit))
        # File size limit
        resource.setrlimit(resource.RLIMIT_FSIZE, (self.file_size_limit, self.file_size_limit))
        # Process limit
        resource.setrlimit(resource.RLIMIT_NPROC, (self.process_limit, self.process_limit))
        
    def _check_resource_violation(self, process) -> str :
        sig_map = {
            signal.SIGXCPU: "CPU Limit",
            signal.SIGKILL: "Memory Limit",
            signal.SIGSEGV: "Memory Corruption",
            signal.SIGXFSZ: "File Size Limit"
        }
        if process.returncode < 0:
           sig = -process.returncode
        else:
           sig = os.WTERMSIG(process.returncode)
        return sig_map.get(sig, "No violation")
    
    def execute_file(self, file_path: str, args: Optional[List[str]] = None) -> dict:
        """Safely execute a file with strict controls"""
        
        if not os.path.isfile(file_path):
            self.logger.error(f"File not found: {file_path}")
            return {"error": "File not found"}
        
        if not os.access(file_path, os.X_OK):
            return {"error": "File not executable"}

        args = args or []
        full_command = [file_path] + args
        self.logger.info(f"Executing command: {' '.join(full_command)}")

        try:
            # Sanitazation 
            clean_env = {k: v for k, v in os.environ.items() if k.startswith('SAFE_') or k in ['PATH', 'LANG', 'HOME']}     
            self.logger.info(f"Running with sanitized environment: {list(clean_env.keys())}")
            # Execute process directly with resource limits
            process = subprocess.Popen(
                full_command,
                preexec_fn=self._set_resource_limits,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True  ,
                env=clean_env  
            )

            start_time = time.time()
            timed_out = False 
            try:
                self.logger.info(f"Process started with PID: {process.pid}")
                stdout, stderr = process.communicate(timeout=self.max_execution_time)
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Process {process.pid} timed out, sending SIGKILL")
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                try: 
                    stdout , stderr = process.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    stdout, stderr = process.communicate()
                    timed_out = True
            
            result = {
                "exit_code": process.returncode,
                "stdout": stdout.strip(),
                "stderr": stderr.strip(),
                "execution_time": time.time() - start_time,
                "timed_out" : timed_out,
                "resource_violation" : self._check_resource_violation(process) 
            }
            self.logger.info(f"Execution result: {json.dumps(result)}")
            return result

        except Exception as e:
            error_result = {"error": str(e)}
            self.logger.error(f"Execution failed: {e}")
            self.logger.error(f"Execution result: {json.dumps(error_result)}")
            return error_result

def main():
    if len(sys.argv) < 2:
        print("Usage: python execute.py <file_path> [args...] [--cpu-limit SECONDS]")
        sys.exit(1)
    # Parse arguments
    args = sys.argv[1:]
    override_params = {}
    config_path = '/app/Secure-Docker-Container/config/execution_limits.json'
    
    # Check for config file path
    if '--config' in args:
        try:
            config_index = args.index('--config')
            config_path = args[config_index + 1]
            args.pop(config_index + 1)
            args.pop(config_index)
        except (ValueError, IndexError):
            print("Invalid config path")
            sys.exit(1)
            
    # Parse CPU time limit if provided
    if '--cpu-limit' in args:
        try:
            limit_index = args.index('--cpu-limit')
            override_params['cpu_time_limit'] = int(args[limit_index + 1])
            args.pop(limit_index + 1)
            args.pop(limit_index)
        except (ValueError, IndexError):
            print("Invalid CPU time limit")
            sys.exit(1)
    
    # Get file path and remaining arguments
    file_path = args[0]
    execution_args = args[1:] if len(args) > 1 else []

    # Initialize executor with custom CPU limit if provided
    executor = SafeExecutor(config_path=config_path, **override_params)
    
    # Execute file and print results
    result = executor.execute_file(file_path, execution_args)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
