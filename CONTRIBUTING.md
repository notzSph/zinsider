# Contributing

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Run the test suite with:

```bash
python -m pytest
```

## Pull requests

- Keep changes focused and explain the operational impact.
- Add or update tests for behavioural changes.
- Do not commit `.env`, credentials, runtime databases, logs, or generated caches.
- Run the tests and review `git diff --check` before submitting.
