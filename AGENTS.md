# Working in agentsweep

See what your AI agent tools have piled up on disk, and clear it safely. Nothing is deleted; it goes to a trash folder you can restore from.

## Run the tests

You need Python 3.9 or newer.

```bash
python3 -m unittest discover -s tests
```

Every test should pass before you start and after you finish.

## Where things are

- `tests/`: the tests

## Before you commit

- Make sure the tests pass.
- Put changes people will notice in `CHANGELOG.md`.
- Do not put real passwords, keys or private data in test files or examples. Use made-up ones.
