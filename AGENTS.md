# Agent Guidelines

This file provides guidance when working with code in this repository.

## Project Overview

See this projects README.md for an overview of the project, and ADR documents in docs/adr/ for architectural decisions.

## Development Commands

**IMPORTANT**: Always use the Makefile commands for development tasks.

### Setup
```bash
make setup  # Set up venv and sync dependencies with uv
```

### Testing
```bash
make test                                    # Run all tests with pytest and coverage
uv run pytest tests/test_foo.py             # Run specific test file
uv run pytest tests/test_foo.py::test_name  # Run specific test
uv run pytest -v                             # Verbose output
```

### Code Quality
```bash
make lint   # Check code with ruff
make fix    # Auto-fix ruff issues
make type   # Type check with mypy (strict mode)
make radon  # Check cyclomatic complexity and maintainability
make ci     # Run all CI checks (lint + type + test + radon)
```

**Before completing any feature**, run `make ci` to ensure all checks pass.

## Code Quality Requirements

Writing guidance:

- No comments or docstrings (enforced by ast-grep rules in `.ast-grep/rules`); prefer clear naming, types, and tests
- Use `# WHY:` only for a non-obvious rationale a reviewer would otherwise ask about

## Execution Preferences

- **Subagent-Driven Development**: Prefer using `superpowers:subagent-driven-development` for executing implementation plans within the same session.

## Lessons Learned

### Use quiet-runner for intermediate verification

**Problem**: When making multiple changes to fix CI issues (like refactoring for complexity or fixing test failures), it's easy to introduce new issues or not fully solve the original problem.

**Solution**: Use quiet-runner between major changes to catch issues early. For test failures, run the specific failing test directly with verbose output (`uv run pytest tests/test_file.py::test_name -xvs`) to see detailed error messages.

**Directive**: When fixing CI failures:
1. First use quiet-runner to identify all issues
2. For test failures, run the specific failing test with verbose output to understand the exact failure
3. After each significant code change, use quiet-runner again to verify the fix doesn't break other tests or introduce new issues
4. Continue until quiet-runner reports "success"

## Project Structure

```
{{cookiecutter.package_name}}/       # Main package source code
tests/          # Test files (mirror treepeat/ structure)
docs/adr/       # Architecture Decision Records
```
