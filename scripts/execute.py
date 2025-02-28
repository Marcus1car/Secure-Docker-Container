import os
import sys
import subprocess
import resource
import time
import logging
import json
import signal
from typing import List, Optional

class SafeExecutor:
    def __init__(self, 
                 log_dir: str = '/app/Secure-Docker-Container/logs', 
                 max_execution_time: int = 5,  #edited for testing
                 memory_limit: int = 64 * 1024 * 1024,#edited for testing
                 cpu_time_limit: Optional[int] = 2):#edited for testing
        """Initialize SafeExecutor with configurable execution parameters"""
        self.log_dir = os.path.abspath(log_dir)
        self.max_execution_time = max_execution_time
        self.memory_limit = memory_limit
        self.cpu_time_limit = cpu_time_limit
        os.makedirs(self.log_dir, exist_ok=True)
        # Configure logging
        self.logger = logging.getLogger('SafeExecutor')
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging with file rotation"""
        log_file = os.path.join(self.log_dir, 'execution.log')
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
        
    
    def _set_resource_limits(self):
        """Set resource limits for executed process"""
        # Memory limit (RLIMIT_AS = address space limit)
        resource.setrlimit(resource.RLIMIT_AS, (self.memory_limit, self.memory_limit))
        
        # CPU time limit (seconds)
        if self.cpu_time_limit:
            resource.setrlimit(resource.RLIMIT_CPU,(self.cpu_time_limit, self.cpu_time_limit))
        
        # Additional limits (optional)
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024,1024 * 1024))  # 100MB file size ,edited for testing
        resource.setrlimit(resource.RLIMIT_NPROC, (5,5))  # Max 50 processes  ,edited for testing
    
    def _check_resource_violation(self, process: subprocess.Popen) -> str:
        """Determine which resource limit was hit"""
        if process.returncode == -signal.SIGXCPU:
            return "CPU time limit exceeded"
        if process.returncode == -signal.SIGKILL:
            return "Memory limit exceeded"
        return "No resource violation detected"
    
    def execute_file(self, file_path: str, args: Optional[List[str]] = None) -> dict:
        """Safely execute a file with strict controls"""
        if not os.path.isfile(file_path):
            self.logger.error(f"File not found: {file_path}")
            return {"error": "File not found"}

        args = args or []
        full_command = [file_path] + args

        try:
            # Execute process directly with resource limits
            process = subprocess.Popen(
                full_command,
                preexec_fn=self._set_resource_limits,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True  
            )

            start_time = time.time()
            timed_out = False 
            try:
                stdout, stderr = process.communicate(timeout=self.max_execution_time)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpid() , signal.SIGKILL)
                try: 
                    stdout , stderr = process.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpid() , signal.SIGKILL)
                    stdout, stderr = process.communicate()
                    timed_out = True
            
            return {
                "exit_code": process.returncode,
                "stdout": stdout.strip(),
                "stderr": stderr.strip(),
                "execution_time": time.time() - start_time,
                "timed_out " : timed_out,
                "resource_violation" : self._check_resource_violation(process) 
            }

        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            return {"error": str(e)}

def main():
    if len(sys.argv) < 2:
        print("Usage: python execute.py <file_path> [args...] [--cpu-limit SECONDS]")
        sys.exit(1)

    # Parse CPU time limit if provided
    cpu_time_limit = None
    args = sys.argv[1:] 
    if '--cpu-limit' in args:
        try:
            limit_index = args.index('--cpu-limit')
            cpu_time_limit = int(args[limit_index + 1])
            args.pop(limit_index + 1)
            args.pop(limit_index)
        except (ValueError, IndexError):
            print("Invalid CPU time limit")
            sys.exit(1)

    # Get file path and remaining arguments
    file_path = args[0]
    execution_args = args[1:] if len(args) > 1 else []

    # Initialize executor with custom CPU limit if provided
    executor = SafeExecutor(cpu_time_limit=cpu_time_limit)
    
    # Execute file and print results
    result = executor.execute_file(file_path, execution_args)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
