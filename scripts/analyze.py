import os
import sys
import logging
import magic
import yara
import json
from typing import Dict, Any


DEFAULT_LOG_DIR = os.environ.get(
    "SDC_LOG_DIR", "/app/Secure-Docker-Container/logs"
)
DEFAULT_WHITELIST = os.environ.get(
    "SDC_WHITELIST", "/app/Secure-Docker-Container/config/whitelist.json"
)
DEFAULT_RULES = os.environ.get("SDC_RULES", "/app/yara-rules/index.yar")


class FileAnalyzer:
    def __init__(self, log_dir: str = None, whitelist_path: str = None,
                 rules_path: str = None):
        self.log_dir = log_dir or DEFAULT_LOG_DIR
        self.whitelist_path = whitelist_path or DEFAULT_WHITELIST
        self.rules_path = rules_path or DEFAULT_RULES

        os.makedirs(self.log_dir, exist_ok=True)
        self.logger = self._setup_logging()

        self.yara_rules = self._load_yara_rules()
        self.whitelist = self._load_whitelist()

    def _setup_logging(self) -> logging.Logger:
        """Per-instance logger.

        logging.basicConfig configures the root logger once per process, so it
        cannot support two analyzers with different log destinations.
        """
        logger = logging.getLogger("FileAnalyzer.%s" % self.log_dir)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not logger.handlers:
            handler = logging.FileHandler(
                os.path.join(self.log_dir, "file_analysis.log")
            )
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logger.addHandler(handler)
        return logger

    def _load_whitelist(self) -> list:
        try:
            with open(self.whitelist_path) as f:
                return json.load(f)["allowed_mime_types"]
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
            rules = yara.compile(filepath=self.rules_path)
            self.logger.info(f"YARA rules loaded from {self.rules_path}")
            return rules
        except (yara.Error, OSError) as e:
            # Fail closed. A scanner that cannot load must not be mistaken for
            # a scanner that found nothing.
            self.logger.critical(f"YARA rule loading failed: {e}")
            raise RuntimeError(
                f"YARA rules could not be loaded from {self.rules_path}: {e}"
            ) from e

    def scan_with_yara(self, file_path: str) -> dict:
        """Scan a file. `scanned` records whether the scan actually happened."""
        try:
            matches = self.yara_rules.match(file_path)
            return {
                "scanned": True,
                "malicious": len(matches) > 0,
                "matches": [str(m) for m in matches],
            }
        except Exception as e:
            self.logger.error(f"YARA scan error: {e}")
            # No "malicious" key on this path — absence of evidence is not
            # evidence of absence.
            return {"scanned": False, "error": str(e), "matches": []}

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Perform a comprehensive analysis of the file."""
        if not os.path.isfile(file_path):
            self.logger.error(f"File not found: {file_path}")
            return {"error": "File not found"}

        file_type = self.get_file_type(file_path)
        is_whitelisted = file_type in self.whitelist

        analysis_result = {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "file_type": file_type,
            "whitelist_status": "allowed" if is_whitelisted else "blocked",
            "yara_result": self.scan_with_yara(file_path),
        }
        analysis_result["threat_level"] = self._assess_threat(analysis_result)

        self.logger.info(f"File analyzed: {json.dumps(analysis_result, indent=2)}")
        return analysis_result

    def _assess_threat(self, result: dict) -> str:
        """Most severe condition wins.

        Evidence of malware outranks a policy miss. A scan that did not run is
        never reported as clean.
        """
        yara_result = result.get("yara_result", {})

        if not yara_result.get("scanned", False):
            return "unknown"
        if yara_result.get("malicious", False):
            return "high"
        if result.get("whitelist_status") == "blocked":
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
