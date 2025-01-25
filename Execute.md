
  Optional CPU time limit :
  ```
  # Run with default settings
python execute.py /path/to/file

  # Specify a 5-second CPU time limit , Default max execution time: 60 seconds
python execute.py /path/to/file --cpu-limit 5
  ```
  Default memory limit: 256 MB

  Logging:
  - Creates `execution.log` file in the `logs` directory.
  - Configures log format with timestamp, logger name, log level

  Executable files:


  Executable files:
  - Linux binaries
  - Shell scripts
  - Python scripts
  - Compiled programs
    
  Potential limitations:
  - Large files (memory constraints)
  - Highly interactive programs
  - Graphical applications
  - Long-running processes
    
  Key restrictions:
  - No network access
  - Limited CPU/memory resources
  - Isolated execution environment

  
    
