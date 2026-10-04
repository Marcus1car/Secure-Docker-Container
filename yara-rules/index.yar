// Compile entry point for analyze.py (SDC_RULES).
// Restored 2026-09-17 — the original was deleted by commit 66f3532 on
// 2025-03-15 while analyze.py kept compiling this path, so every scan
// silently reported files as clean.

include "detection.yar"
include "malware_detection.yar"

// enhanced_rules.yar is deliberately NOT included. It has a malformed hex
// escape (/\x[0-9A-F]{2}/), a base64 rule broad enough to match most binaries,
// and it includes malware_detection.yar itself, which would duplicate every
// rule identifier above. Fix those before re-enabling it.
