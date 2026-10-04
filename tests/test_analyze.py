import os

import pytest

from analyze import FileAnalyzer


def test_paths_are_injectable(tmp_path, rules_path, whitelist_path):
    log_dir = tmp_path / "logs"
    analyzer = FileAnalyzer(
        log_dir=str(log_dir),
        whitelist_path=whitelist_path,
        rules_path=rules_path,
    )
    assert analyzer.log_dir == str(log_dir)
    assert analyzer.whitelist_path == whitelist_path
    assert analyzer.rules_path == rules_path


def test_log_dir_is_created_if_missing(tmp_path, rules_path, whitelist_path):
    """analyze.py had no makedirs, unlike execute.py."""
    log_dir = tmp_path / "does" / "not" / "exist"
    FileAnalyzer(
        log_dir=str(log_dir),
        whitelist_path=whitelist_path,
        rules_path=rules_path,
    )
    assert os.path.isdir(str(log_dir))


def test_two_instances_log_to_their_own_files(tmp_path, rules_path, whitelist_path):
    """logging.basicConfig would have made the second instance write to the first's file."""
    a_dir = tmp_path / "a"
    b_dir = tmp_path / "b"
    a = FileAnalyzer(log_dir=str(a_dir), whitelist_path=whitelist_path, rules_path=rules_path)
    b = FileAnalyzer(log_dir=str(b_dir), whitelist_path=whitelist_path, rules_path=rules_path)
    a.logger.info("from-a")
    b.logger.info("from-b")
    a_log = (a_dir / "file_analysis.log").read_text()
    b_log = (b_dir / "file_analysis.log").read_text()
    assert "from-a" in a_log and "from-b" not in a_log
    assert "from-b" in b_log and "from-a" not in b_log


def test_whitelist_loads_from_injected_path(tmp_path, rules_path):
    custom = tmp_path / "wl.json"
    custom.write_text('{"allowed_mime_types": ["application/x-made-up"]}')
    analyzer = FileAnalyzer(
        log_dir=str(tmp_path / "logs"),
        whitelist_path=str(custom),
        rules_path=rules_path,
    )
    assert analyzer.whitelist == ["application/x-made-up"]


def test_rules_actually_compile(tmp_path, rules_path, whitelist_path):
    """Guards the 2025 regression: index.yar was deleted and nothing noticed."""
    analyzer = FileAnalyzer(
        log_dir=str(tmp_path / "logs"),
        whitelist_path=whitelist_path,
        rules_path=rules_path,
    )
    assert analyzer.yara_rules is not None


def test_pe_sample_matches(tmp_path, rules_path, whitelist_path, samples_dir):
    analyzer = FileAnalyzer(
        log_dir=str(tmp_path / "logs"),
        whitelist_path=whitelist_path,
        rules_path=rules_path,
    )
    result = analyzer.scan_with_yara(os.path.join(samples_dir, "dummy.pe"))
    assert result["scanned"] is True
    assert result["malicious"] is True
    assert result["matches"]


def test_clean_sample_does_not_match(tmp_path, rules_path, whitelist_path, samples_dir):
    analyzer = FileAnalyzer(
        log_dir=str(tmp_path / "logs"),
        whitelist_path=whitelist_path,
        rules_path=rules_path,
    )
    result = analyzer.scan_with_yara(os.path.join(samples_dir, "clean.txt"))
    assert result["scanned"] is True
    assert result["malicious"] is False
    assert result["matches"] == []


def test_missing_rules_file_is_fatal(tmp_path, whitelist_path):
    """A broken scanner must never look like a working one."""
    with pytest.raises(RuntimeError):
        FileAnalyzer(
            log_dir=str(tmp_path / "logs"),
            whitelist_path=whitelist_path,
            rules_path=str(tmp_path / "no-such-index.yar"),
        )


@pytest.fixture
def analyzer(tmp_path, rules_path, whitelist_path):
    return FileAnalyzer(
        log_dir=str(tmp_path / "logs"),
        whitelist_path=whitelist_path,
        rules_path=rules_path,
    )


def test_eicar_in_whitelisted_file_is_not_low(analyzer, tmp_path, eicar_bytes):
    """EICAR inside a whitelisted text/plain file used to score "low"."""
    target = tmp_path / "harmless_looking.txt"
    target.write_bytes(eicar_bytes)
    result = analyzer.analyze_file(str(target))
    assert result["whitelist_status"] == "allowed"
    assert result["yara_result"]["malicious"] is True
    assert result["threat_level"] == "high"


def test_yara_hit_outranks_whitelist_miss(analyzer, samples_dir):
    """A malware match must not score below a MIME-type miss."""
    malware = analyzer.analyze_file(os.path.join(samples_dir, "dummy.pe"))
    benign_unlisted = analyzer.analyze_file(
        os.path.join(samples_dir, "safe_script.sh")
    )
    assert malware["threat_level"] == "high"
    assert benign_unlisted["whitelist_status"] == "blocked"
    assert benign_unlisted["threat_level"] == "medium"


def test_clean_whitelisted_file_is_low(analyzer, samples_dir):
    result = analyzer.analyze_file(os.path.join(samples_dir, "clean.txt"))
    assert result["whitelist_status"] == "allowed"
    assert result["threat_level"] == "low"


class ExplodingRules:
    """Stand-in for a compiled rule set that fails at match time.

    yara.Rules is a C extension type and does not reliably accept attribute
    assignment, so substitute the whole object rather than patching its method.
    """

    def match(self, _path):
        raise RuntimeError("scanner exploded")


def test_scan_failure_yields_unknown_not_low(analyzer, tmp_path):
    """A broken scan must never be reported as clean."""
    target = tmp_path / "ordinary.txt"
    target.write_text("nothing interesting here")

    analyzer.yara_rules = ExplodingRules()
    result = analyzer.analyze_file(str(target))
    assert result["yara_result"]["scanned"] is False
    assert result["threat_level"] == "unknown"
