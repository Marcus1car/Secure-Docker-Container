import os
import sys
import logging
import magic
import yara
import json
from typing import Dict, Any
from pathlib import Path


class FileAnalyzer:
    def __init__(self, log_path: str = '/app/Secure-Docker-Container/logs/file_analysis.log'):
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=log_path,
            filemode='a'  # Append mode to allow multiple script logs
        )
        self.logger = logging.getLogger(__name__)
        self.yara_rules = self._load_yara_rules()
        self.whitelist = self._load_whitelist()

    def _load_whitelist(self) -> list:
        config_path = Path('/app/Secure-Docker-Container/config/whitelist.json')
        try:
            with open(config_path) as f:
                return json.load(f)['allowed_mime_types']
        except Exception as e:
            self.logger.error(f"Whitelist loading error: {e}")
            return []
    
    
    def get_file_type(self, file_path: str) -> str:
        """
        Detect file type using python-magic.
        """
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path)
        except Exception as e:
            self.logger.error(f"File type detection error: {e}")
            return "Unknown"

    def _load_yara_rules(self):
        try:
            # Load all YARA rules from directory
            rules = yara.compile('/app/yara-rules/index.yar')
            self.logger.info("YARA rules loaded successfully")
            return rules
        except yara.Error as e:
            self.logger.error(f"YARA rule loading error: {e}")
            return None

    def scan_with_yara(self, file_path: str) -> dict:
        """
        Scan the file with YARA rules
        """
        if not self.yara_rules:
            return {
            "error": "YARA rules not loaded",
            "malicious": False,  # Add default
            "matches": []         # Add default
            }
        try:
            matches = self.yara_rules.match(file_path)
            return {
                "malicious": len(matches) > 0,
                "matches": [str(m) for m in matches]
            }
        except Exception as e:
            self.logger.error(f"YARA scan error: {e}")
            return {
            "error": str(e),
            "malicious": False,  # Add default
             "matches": []         # Add default
            }

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Perform a comprehensive analysis of the file.
        """
        # Validate file existence
        if not os.path.isfile(file_path):
            self.logger.error(f"File not found: {file_path}")
            return {"error": "File not found"}
        
        file_type = self.get_file_type(file_path)
        is_whitelisted = file_type in self.whitelist

        
        # Gather file details
        analysis_result = {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "file_type": self.get_file_type(file_path),
            "whitelist_status": "allowed" if is_whitelisted else "blocked",
            "yara_result": self.scan_with_yara(file_path)
        }
        
        analysis_result["threat_level"] = self._assess_threat(analysis_result)
        # Log the analysis result
        self.logger.info(f"File analyzed: {json.dumps(analysis_result, indent=2)}")

        return analysis_result

    def _assess_threat(self, result: dict) -> str:
        if result["whitelist_status"] == "blocked":
            return "high"
        
        yara_result = result.get("yara_result", {})
        if yara_result.get("malicious", False):
            return "medium"
        
        return "low"


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <file_path>")
        sys.exit(1)

    analyzer = FileAnalyzer()
    result = analyzer.analyze_file(sys.argv[1])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
