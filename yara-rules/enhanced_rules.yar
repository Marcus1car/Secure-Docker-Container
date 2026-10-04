// Enhanced YARA Rules
include "malware_detection.yar"

// Detect script files
rule script_file {
    meta:
        description = "Detects common script file types"
    strings:
        $shebang = "#!/" 
        $ps1 = "powershell" nocase
        $bash = "#!/bin/bash"
    condition:
        any of them
}

// Detect obfuscated code
rule obfuscation_techniques {
    strings:
        $base64 = /[A-Za-z0-9+\/]{32,}={0,2}/  // Base64 patterns
        $hex_encoded = /\x[0-9A-F]{2}/  // Hex encoding
    condition:
        any of them and filesize < 100KB
}

// Detect common exploit patterns (example: buffer overflow)
rule buffer_overflow_attempt {
    strings:
        $long_string = /AAAAAAAAAAAAAAAAAAAA{20,}/  // Excessive repeated characters
    condition:
        $long_string
}

// Add more rules from sources like:
// https://github.com/Yara-Rules/rules