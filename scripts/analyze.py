import os
import sys
import logging
import magic
import pyclamd
import json
from typing import Dict, Any







class FileAnalyzer:
    def __init__(self, log_path: str = '/app/Secure-Docker-Container/logs/file_analysis.log'):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=log_path,
            filemode='a'  # Append mode to allow multiple script logs
        )
        self.logger = logging.getLogger(__name__)

       # Initialize ClamAV scanner
        try:
            self.cd = pyclamd.ClamdUnixSocket()
            if not self.cd.ping():
                self.logger.error("ClamAV daemon is not running")
        except Exception as e:
            self.logger.error(f"ClamAV initialization error: {e}")
            self.cd = None

    
    def get_file_type(self, file_path: str) -> str:
        """
        Detect file type using python-magic
        """
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path)
        except Exception as e:
            self.logger.error(f"File type detection error: {e}")
            return "Unknown"
        
        

    def scan_with_clamav(self, file_path: str) -> Any:
        if not self.cd:
            self.logger.warning("ClamAV not initialized")
            return None

        try:
            return self.cd.scan_file(file_path)
        except Exception as e:
            self.logger.error(f"ClamAV scan error: {e}")
            return None
        


    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Comprehensive file analysis
        """
        # Validate file existence
        if not os.path.isfile(file_path):
            self.logger.error(f"File not found: {file_path}")
            return {"error": "File not found"}

        # Gather file details
        analysis_result = {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "file_type": self.get_file_type(file_path),
            "clamav_result": self.scan_with_clamav(file_path),
            #"check" = True
        }

        # Log the analysis
        self.logger.info(f"File analyzed: {json.dumps(analysis_result, indent=2)}")

        return analysis_result



def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <file_path>")
        sys.exit(1)

    analyzer = FileAnalyzer()
    result = analyzer.analyze_file(sys.argv[1])
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
    
    
    
