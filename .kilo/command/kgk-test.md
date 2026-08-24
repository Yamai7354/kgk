---
description: Run KGK test suite
agent: kgk-tester
---
Run pytest on the KGK project.

$ARGUMENTS are passed directly to pytest.

Examples:
- `/kgk-test` — run full test suite
- `/kgk-test -k test_retract` — run specific tests
- `/kgk-test -v` — verbose output
- `/kgk-test --tb=short` — short traceback format

Command:
```bash
pytest tests/ $ARGUMENTS
```

If tests fail, analyze the failures and suggest fixes referencing the specific module and line numbers.
