
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
  - Configures log format with:
    - Timestamp
    - Logger name
    - Log level
    - Writes some stuff in markdown
    
