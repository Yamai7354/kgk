---
description: Run Ruff linter on KGK
agent: kgk-developer
---
Run Ruff to check code quality.

$ARGUMENTS are passed to `ruff check`.

Examples:
- `/kgk-lint` — check all files
- `/kgk-lint --fix` — auto-fix what can be fixed
- `/kgk-lint models/` — check specific module

Command:
```bash
ruff check . $ARGUMENTS
```

Report violations by file and line, then suggest fixes following the project's line-length = 100 rule.
