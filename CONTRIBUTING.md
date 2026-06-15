# Contributing

Thanks for your interest in SignalLock.

## Scope

This project is a defensive cybersecurity research effort. Contributions should support:

- password security research,
- privacy-preserving risk assessment,
- context-aware authentication hardening,
- explainable defensive tooling.

Contributions that move the project toward offensive targeting, exploit-ready password guessing, or unauthorized profiling are out of scope.

## Contribution Guidelines

1. Open an issue or discussion before large changes.
2. Keep changes narrowly scoped and well documented.
3. Add or update tests when code is introduced.
4. Prefer synthetic, anonymized, or consent-based data only.
5. Document ethical and security implications of any new module.

## Coding Expectations

- Python 3.11+
- clear module boundaries,
- typed interfaces where practical,
- concise documentation for public functions,
- reproducible experiments.

## Running Tests

The test suite uses package-relative fixtures, so run it from the repo root with
the top-level dir set explicitly:

```bash
.venv/bin/python -m unittest discover -t . -s tests -v
```

The `[demo]` extra (bcrypt) is needed for `tests/test_demo.py`; it skips cleanly
without it.

## Branching

- `main` should remain stable.
- Feature work should happen on short-lived branches.

## Commit Style

Suggested prefixes:

- `docs:`
- `proposal:`
- `feat:`
- `fix:`
- `test:`
- `refactor:`

## Responsible Research

If a proposed contribution could materially increase offensive misuse risk, it should be redesigned or declined.
