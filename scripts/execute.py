import os
import sys
import subprocess
import resource
import time
import logging
import json
import signal
from typing import List, Optional , Any , Dict


# Single source of truth for the limits. load_config falls back to it, and
# SafeExecutor merges every config under it, so a key missing from a partial
# config file can never leave a limit unset.
DEFAULT_CONFIG = {
    "memory_limit": 64 * 1024 * 1024,       # 64MB
    "cpu_time_limit": 30,                   # 30 seconds CPU time
    "file_size_limit": 10 * 1024 * 1024,    # 10MB file size limit
    "process_limit": 5,                     # Max 5 processes
    "max_execution_time": 5                 # 5 seconds wall time
}


def load_config(config_path='/app/Secure-Docker-Container/config/execution_limits.json') -> Dict[str, Any]:
    """
    Load resource limits from a configuration file.
    Falls back to default values if config file is not found or invalid.
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            # bool is a subclass of int, so it must be excluded explicitly.
            if not all(
                isinstance(v, int) and not isinstance(v, bool)
                for v in config.values()
            ):
                raise ValueError("Config values must be integers")
            return config

    except (FileNotFoundError, json.JSONDecodeError, PermissionError,
            ValueError, TypeError, AttributeError) as e:
        print(f"Warning: Could not load config from {config_path}: {str(e)}")
        # A copy: callers update the returned dict.
        return dict(DEFAULT_CONFIG)


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
        
        # Defaults first, then the config file, then explicit overrides. A partial
        # config used to leave cpu_time_limit as None, which silently skipped
        # RLIMIT_CPU, and fell back to a 1 MB file-size limit instead of 10 MB.
        self.config = {**DEFAULT_CONFIG, **load_config(config_path), **override_params}

        # Extract configuration values
        self.log_dir = os.path.abspath(log_dir)
        self.max_execution_time = self.config["max_execution_time"]
        self.memory_limit = self.config["memory_limit"]
        self.cpu_time_limit = self.config["cpu_time_limit"]
        self.file_size_limit = self.config["file_size_limit"]
        self.process_limit = self.config["process_limit"]
        
       # Setup logging directory
        os.makedirs(self.log_dir, exist_ok=True)
        # Configure logging
        self.logger = self._setup_logging()
        self.logger.info(f"SafeExecutor initialized with config: {json.dumps(self.config, indent=2)}")

    def _setup_logging(self) -> logging.Logger:
        """Per-instance logger.

        Mirrors analyze.py's FileAnalyzer._setup_logging. A single global
        `logging.getLogger('SafeExecutor')` with an unconditional addHandler
        means a second instance in the same process (e.g. a future policy
        gate that runs a FileAnalyzer and a SafeExecutor together) adds a
        second handler to the *same* logger object, so both instances' lines
        land in whichever log file the handler-list happens to put first.
        Keying the logger name by log_dir and guarding addHandler gives each
        instance (and each distinct log_dir) its own logger and its own file.
        """
        logger = logging.getLogger("SafeExecutor.%s" % self.log_dir)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not logger.handlers:
            log_file = os.path.join(self.log_dir, 'execution.log')
            file_handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        return logger


    def _set_resource_limits(self):
        """Set resource limits for executed process based on configuration"""
        # Memory limit (RLIMIT_AS = address space limit)
        resource.setrlimit(resource.RLIMIT_AS, (self.memory_limit, self.memory_limit))
        # CPU time limit (seconds)
        if self.cpu_time_limit:
            # Soft != hard deliberately. The kernel
            # sends SIGXCPU at the soft limit and SIGKILL at the hard limit;
            # with soft == hard both fire in the same instant and SIGKILL wins
            # the race, so every CPU-limit kill was reported as "Killed
            # (possible OOM)" instead of "CPU Limit" (the limit was enforced,
            # but reported as a memory problem). Splitting them gives the process a
            # window to receive SIGXCPU and die from that signal instead. The
            # cost: a process that catches/ignores SIGXCPU gets up to one
            # extra second of CPU time before the hard limit kills it. That is
            # accepted on purpose — max_execution_time (wall clock) remains
            # the real backstop, and a correctly-labelled violation is worth
            # one second of slack.
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.cpu_time_limit, self.cpu_time_limit + 1),
            )
        # File size limit
        resource.setrlimit(resource.RLIMIT_FSIZE, (self.file_size_limit, self.file_size_limit))
        # Process limit
        resource.setrlimit(resource.RLIMIT_NPROC, (self.process_limit, self.process_limit))
        
    def _check_resource_violation(self, process, timed_out: bool = False) -> str:
        """Classify why a process ended.

        subprocess already decodes wait status: a negative returncode means
        "killed by signal -returncode", and any value >= 0 is an ordinary exit.
        Passing a plain exit code to os.WTERMSIG reinterprets it as a signal
        number: exit 9 read as SIGKILL, exit 24 as SIGXCPU.
        """
        if timed_out:
            # We sent the SIGKILL ourselves; it is not evidence of a limit.
            return "Timeout"

        returncode = process.returncode
        if returncode is None or returncode >= 0:
            return "No violation"

        sig = -returncode
        sig_map = {
            signal.SIGXCPU: "CPU Limit",
            signal.SIGXFSZ: "File Size Limit",
            signal.SIGSEGV: "Memory Corruption",
            signal.SIGKILL: "Killed (possible OOM)",
        }
        return sig_map.get(sig, f"Killed by signal {sig}")
    
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
                stdout, stderr = process.communicate(
                    timeout=self.max_execution_time
                )
            except subprocess.TimeoutExpired:
                # This flag used to be set only in the nested handler,
                # so the common case reported timed_out=False.
                timed_out = True
                self.logger.warning(
                    f"Process {process.pid} timed out, sending SIGKILL"
                )
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                try:
                    stdout, stderr = process.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    stdout, stderr = process.communicate()

            result = {
                "exit_code": process.returncode,
                "stdout": stdout.strip(),
                "stderr": stderr.strip(),
                "execution_time": time.time() - start_time,
                "timed_out": timed_out,
                "resource_violation": self._check_resource_violation(
                    process, timed_out
                ),
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
