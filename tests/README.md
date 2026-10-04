# Running the test suite

There are two ways to run the tests. Both use the same `tests/` directory
and the same `requirements-dev.txt`.

## Host venv (primary dev loop)

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt -r requirements.txt
PYTHONPATH="$PWD/scripts" ./.venv/bin/python -m pytest tests/ -v
```

`.venv/` is git-ignored; recreate it as needed. This is the fastest path
for day-to-day development.

`python-magic` (used by `scripts/analyze.py`) is a thin wrapper around the
system `libmagic`. The pip package alone is not enough for the host venv
path: without `libmagic1` (Debian/Ubuntu) or the equivalent package for your
distro installed system-wide, `import magic` fails with an unhelpful error
(commonly `ImportError: failed to find libmagic`). The container profile
below does not have this problem — `libmagic1` is installed in the image.

## Container profile (fidelity / CI)

Runs pytest inside the same image the production container uses, as
uid 10001 with no network access — closer to how the tool actually runs.

```bash
docker compose build secure-container
docker compose --profile test build test
docker compose --profile test run --rm test
```

Tests must never write into the bind-mounted repo (`/work`): the
container user cannot write there. Use pytest's `tmp_path` fixture for
any file the tests need to create.

**What this profile does and does not validate.** The `test` service
bind-mounts the repo to `/work` and runs pytest against `/work/scripts` —
the same files on your checkout, imported live. It does *not* exercise the
image's baked-in copies under `/app/Secure-Docker-Container/`, which is
where the `Dockerfile`'s `COPY` instructions place the production code. A
bug introduced only by the `COPY` step (wrong source path, stale layer, a
file silently excluded) will not be caught here — this is precisely how the
`Dockerfile` `COPY` bug (which stopped the image from building) got past testing before. This profile is
a fast regression guard for the runtime *logic*; it is not a substitute for
also exercising the `analyze`/`execute` profiles (or `smoke_entrypoints.sh`)
against the actual built image.
