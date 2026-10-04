# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `.github/workflows/ci.yml` — continuous integration on every push and pull request:
  the test suite on Python 3.10 and 3.12, the production and test image builds, the test
  suite inside the container, and the smoke test of the documented entry points.
- A CI status badge at the top of the README.

### Fixed

- **A config file that omitted `cpu_time_limit` silently removed the CPU limit.** The
  missing key became `None`, and the limit was then skipped entirely. Missing keys now fall
  back to the defaults.
- **The default file-size limit disagreed with itself:** 1 MB in `SafeExecutor`, 10 MB in
  `load_config`. Both now use the same `DEFAULT_CONFIG` (10 MB).
- `tests/smoke_entrypoints.sh` no longer lets `docker compose run` consume its caller's
  standard input.

## 2026-10-04 — Repair and test suite

The project could not build its Docker image, and its YARA scanning had silently stopped
working in March 2025. This release fixes both, repairs how threats and resource limits are
reported, adds a 29-test suite, and corrects the documentation so every documented command
works.

16 files changed, 778 insertions, 105 deletions.

### Added

**New files**

- `yara-rules/index.yar` — restores the rule file `analyze.py` loads, deleted in March 2025.
  It includes `detection.yar` and `malware_detection.yar`.
- `tests/test_harness.py` — 3 tests checking the test setup itself.
- `tests/test_analyze.py` — 12 tests for the analyzer.
- `tests/test_execute.py` — 14 tests for the sandbox.
- `tests/conftest.py` — shared test helpers, including an EICAR test file built at runtime.
- `tests/smoke_entrypoints.sh` — checks that the 5 documented commands actually run, and stops
  with a clear message if `logs/` isn't set up.
- `tests/README.md` — how to run the tests on the host and in the container.
- `Dockerfile.test` — a test-only image built on top of the production one, so the production
  image never contains pytest.
- `requirements-dev.txt` — `pytest>=8.0`. Test-only; `requirements.txt` is unchanged.
- `.gitignore` — ignores Claude Code files, Python caches, virtualenvs and `logs/`.

**New features in existing files**

- `analyze.py` — the log, whitelist and rule paths can be passed to the constructor or set with
  `SDC_LOG_DIR`, `SDC_WHITELIST` and `SDC_RULES`. The container defaults are unchanged.
- `analyze.py` — every scan result has a `scanned` field, and there is a new `unknown` threat
  level.
- `execute.py` — new violation labels: `"Timeout"`, `"Killed (possible OOM)"` and
  `"Killed by signal N"`.
- `docker-compose.yml` — a new `test` profile that runs the tests inside the container.
- `README.md` — a "Run the tests" section.

### Fixed

| What was broken | Now |
|---|---|
| The image couldn't build (`COPY … .` needs a trailing `/`) | `COPY … ./` builds |
| YARA never loaded; every file was reported clean | Rules load. If they can't, the program stops with an error instead of carrying on |
| A crashed scan scored the file `low` | It scores `unknown` |
| An unlisted MIME type outranked confirmed malware | Order is now: scan failed → `unknown`, malware → `high`, unlisted type → `medium`, otherwise `low` |
| `exit 9` was reported as "Memory Limit", `exit 24` as "CPU Limit" | A normal exit code is no longer mistaken for a kill signal |
| A CPU-limit kill was reported as a memory problem | Reported as `"CPU Limit"` (the soft and hard CPU limits are now different) |
| `timed_out` was false on almost every real timeout | It is set on the path that actually runs |
| A config value that was a decimal, a `true`/`false`, or a list crashed the program or was accepted | Falls back to defaults |
| `analyze.py` crashed if `logs/` was missing | Creates the folder |
| Two analyzers (or executors) in one process wrote to each other's log files | Each gets its own log |
| `docker compose --profile analyze up` always printed "File not found" | Default commands point at real sample files |
| README examples put `-v` after the service name, so none of them worked | `-v` goes before the service name |

Also: removed a trailing space from the `enhanced_rules.yar` filename (contents unchanged),
removed a duplicate file-type check per scan, and fixed the comment typo `Defaut Config`.

### Changed

Behaviour that changed — check whether anything depends on it:

- **`FileAnalyzer`'s first parameter was renamed** from `log_path` (a file) to `log_dir`
  (a folder). Nothing in the repository used it.
- **`FileAnalyzer()` now raises `RuntimeError`** if the rules can't load. Before, it started
  anyway and reported every file clean.
- **The JSON output changed shape.** `yara_result` has a new `scanned` field. When a scan fails
  it has no `malicious` field. `threat_level` can be `unknown`.
- **`"Memory Limit"` is never reported any more.** Memory exhaustion doesn't produce a kill
  signal, so the old label was always wrong. As a result, no memory-violation label exists at
  the moment (see Known issues).
- **The same file can get a different verdict.** For example, `samples/safe_script.sh` was
  `high` and is now `medium`.

### Removed

- **From `analyze.py`:**
  - `logging.basicConfig`, which shared one log setup across the whole program.
  - Hard-coded `/app/...` paths inside methods.
  - The unused `pathlib` import.
  - The `return None` on rule-loading failure.
  - The early "YARA rules not loaded" result.
  - Both `"malicious": False  # Add default` fallbacks.
- **From `execute.py`:**
  - The `os.WTERMSIG` call.
  - The rule that turned SIGKILL into "Memory Limit".
  - The `"No violation"` fallback for unknown signals.
  - The shared `SafeExecutor` logger.
  - The `timed_out = True` that only ran in a rarely reached branch.
- **From `docker-compose.yml`:** `depends_on: secure-container` on `analyze` and `execute`.
  It did nothing useful and printed an error on every run.
- **From `README.md`:**
  - References to sample files that don't exist: `suspicious_file`, `test_script.sh`,
    `script.sh`, `document.pdf`, `malware.exe`.
  - The old `docker-compose` (v1) command form.
  - The claim that the whitelist blocks files.

### Not changed

- `entrypoint.sh`, `config/`, `samples/`, `detection.yar`, `malware_detection.yar` and
  `requirements.txt`.
- The rest of the `Dockerfile`: still `ubuntu:22.04`, `gosu` and `netcat`.
- `enhanced_rules.yar` is still excluded from scanning: it contains a malformed pattern that
  would stop the rules from loading.
- No security hardening was added to the containers. That is planned for the next stage.

### Known issues

Not fixed in this release:

- ~~Deleting `cpu_time_limit` from the config silently removes the CPU limit.~~ Fixed — see
  Unreleased.
- No memory-violation label exists: memory exhaustion surfaces as an ordinary exit.
- The `analyze` and `execute` containers have no `cap_drop` or `no-new-privileges`.
- Sandboxed code runs as the same user as the supervisor, so it can overwrite its own config
  and logs.
- The process limit is counted per user, not per sandbox.
- The whitelist doesn't block anything; `execute.py` never reads it.
- ~~The default file-size limit is 1 MB in one place and 10 MB in another.~~ Fixed — see
  Unreleased.
- On a fresh clone, `logs/` is created owned by root and the sandbox can't write to it. The
  smoke test detects this and prints the fix.
- If the whitelist file fails to load, nothing reports it, and every file is treated as not
  whitelisted.
- If a child process of the executed script hits a limit, it isn't reported.
