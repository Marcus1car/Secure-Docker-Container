import json

import pytest

from execute import SafeExecutor


@pytest.fixture
def executor(tmp_path):
    # process_limit is raised above the default 10 because RLIMIT_NPROC is
    # enforced per real UID, and the test runner's own processes share uid 10001.
    # A tight limit here makes these tests flaky, not rigorous.
    return SafeExecutor(
        log_dir=str(tmp_path / "logs"),
        config_path=str(tmp_path / "no-such-config.json"),
        max_execution_time=2,
        process_limit=64,
    )


def test_clean_run_reports_no_violation(executor, make_script):
    script = make_script("ok.sh", "echo hello\n")
    result = executor.execute_file(script)
    assert result["exit_code"] == 0
    assert result["stdout"] == "hello"
    assert result["timed_out"] is False
    assert result["resource_violation"] == "No violation"


def test_nonzero_exit_is_not_read_as_a_signal(executor, make_script):
    """A plain exit 9 was reported as "Memory Limit" by WTERMSIG(9)."""
    script = make_script("bye.sh", "exit 9\n")
    result = executor.execute_file(script)
    assert result["exit_code"] == 9
    assert result["resource_violation"] == "No violation"


def test_exit_24_is_not_read_as_cpu_limit(executor, make_script):
    """A plain exit 24 was reported as "CPU Limit": WTERMSIG(24) == SIGXCPU."""
    script = make_script("bye24.sh", "exit 24\n")
    result = executor.execute_file(script)
    assert result["exit_code"] == 24
    assert result["resource_violation"] == "No violation"


def test_timeout_is_flagged_and_not_called_a_memory_limit(executor, make_script):
    """A timeout used to report timed_out=false, violation="Memory Limit"."""
    script = make_script("sleeper.sh", "sleep 30\n")
    result = executor.execute_file(script)
    assert result["timed_out"] is True
    assert result["resource_violation"] == "Timeout"
    assert result["execution_time"] < 10


def test_missing_file_is_reported(executor, tmp_path):
    result = executor.execute_file(str(tmp_path / "nope.sh"))
    assert result == {"error": "File not found"}


def test_result_is_json_serialisable(executor, make_script):
    script = make_script("ok2.sh", "echo fine\n")
    json.dumps(executor.execute_file(script))


def test_two_instances_log_to_their_own_files(tmp_path):
    """Mirrors test_analyze.py's test of the same name.

    A single global logging.getLogger('SafeExecutor') with an unconditional
    addHandler would make the second instance's lines land in the first
    instance's execution.log (or vice versa, depending on handler order).
    """
    from execute import SafeExecutor

    a_dir = tmp_path / "a"
    b_dir = tmp_path / "b"
    a = SafeExecutor(
        log_dir=str(a_dir),
        config_path=str(tmp_path / "no-such-config.json"),
    )
    b = SafeExecutor(
        log_dir=str(b_dir),
        config_path=str(tmp_path / "no-such-config.json"),
    )
    a.logger.info("from-a")
    b.logger.info("from-b")
    a_log = (a_dir / "execution.log").read_text()
    b_log = (b_dir / "execution.log").read_text()
    assert "from-a" in a_log and "from-b" not in a_log
    assert "from-b" in b_log and "from-a" not in b_log


def test_file_size_violation_is_reported(executor, make_script):
    """A genuine SIGXFSZ death must still surface as a real violation.

    `kill -XFSZ $$` is a shell builtin (no fork), so it deterministically
    probes the same default-action path a real RLIMIT_FSIZE breach takes,
    without depending on RLIMIT_NPROC headroom on the host (a
    script that actually forks, e.g. `dd`, is flaky here because RLIMIT_NPROC
    is enforced against the real UID, which already owns hundreds of
    processes on a dev machine well before the sandbox's own limit).
    Guards against a gutted sig_map: if the lookup
    were replaced by a constant, this would fail alongside the CPU test below.
    """
    script = make_script("fsize.sh", "kill -XFSZ $$\n")
    result = executor.execute_file(script)
    assert result["exit_code"] == -25  # -SIGXFSZ
    assert result["resource_violation"] == "File Size Limit"
    assert result["timed_out"] is False


def test_cpu_limit_violation_is_reported(make_script, tmp_path):
    """A real CPU-limit kill must be labelled "CPU Limit",
    not silently mis-tagged "Killed (possible OOM)".

    max_execution_time is generous (30s) relative to cpu_time_limit (1s) so
    the wall-clock timeout path cannot mask a CPU-limit failure to enforce.
    """
    from execute import SafeExecutor

    executor = SafeExecutor(
        log_dir=str(tmp_path / "logs"),
        config_path=str(tmp_path / "no-such-config.json"),
        max_execution_time=30,
        process_limit=64,
        cpu_time_limit=1,
    )
    script = make_script("burn.sh", "while true; do :; done\n")
    result = executor.execute_file(script)
    assert result["resource_violation"] == "CPU Limit"
    assert result["timed_out"] is False


from execute import load_config

DEFAULTS = {
    "memory_limit": 64 * 1024 * 1024,
    "cpu_time_limit": 30,
    "file_size_limit": 10 * 1024 * 1024,
    "process_limit": 5,
    "max_execution_time": 5,
}


def test_missing_config_falls_back(tmp_path):
    assert load_config(str(tmp_path / "absent.json")) == DEFAULTS


def test_malformed_json_falls_back(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json at all")
    assert load_config(str(bad)) == DEFAULTS


def test_float_value_falls_back_instead_of_crashing(tmp_path):
    """ValueError was raised inside the try but not caught."""
    bad = tmp_path / "float.json"
    bad.write_text('{"memory_limit": 1.5}')
    assert load_config(str(bad)) == DEFAULTS


def test_boolean_value_is_rejected(tmp_path):
    """isinstance(True, int) is True in Python, so bools slipped through."""
    bad = tmp_path / "bool.json"
    bad.write_text('{"memory_limit": true}')
    assert load_config(str(bad)) == DEFAULTS


def test_valid_config_is_used(tmp_path):
    good = tmp_path / "good.json"
    good.write_text('{"memory_limit": 123, "max_execution_time": 7}')
    assert load_config(str(good)) == {"memory_limit": 123, "max_execution_time": 7}
