# Secure-Docker-Container
**Project Overview :**  
Secure Docker Container for File Analysis and Execution 


  Goal: A portable Docker-based environment for analyzing suspicious files and     
  executables.
  Features:
  File scanning and execution.
  Logging system for activity monitoring.
  Debug Mode for user 
  Network isolation for executables.
  Easy setup via docker build and docker run.


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