---
description: Format KGK code with Ruff
agent: kgk-developer
---
Run Ruff formatter on the project.

$ARGUMENTS are passed to `ruff format`.

Examples:
- `/kgk-format` — format all files
- `/kgk-format --check` — check without writing

Command:
```bash
ruff format . $ARGUMENTS
```
