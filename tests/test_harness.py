import os


def test_runner_sees_the_repo(repo_root, samples_dir):
    assert os.path.isfile(os.path.join(repo_root, "docker-compose.yml"))
    assert os.path.isfile(os.path.join(samples_dir, "dummy.pe"))


def test_runtime_deps_are_importable():
    import magic  # noqa: F401
    import yara  # noqa: F401


def test_tmp_path_is_writable(tmp_path):
    target = tmp_path / "probe.txt"
    target.write_text("ok")
    assert target.read_text() == "ok"
