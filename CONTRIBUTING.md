# Contributing to tdpm-sdd-governance

Thank you for your interest in contributing to `tdpm-sdd-governance`! We welcome contributions to our spec-driven development governance engine, auditors, skills, and agents.

## Development Setup

1. **Prerequisites**:
   - Python 3.11+
   - [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`

2. **Clone and Install**:
   ```bash
   git clone https://github.com/aruruka/tdpm-sdd-governance.git
   cd tdpm-sdd-governance
   uv sync --all-extras
   ```

3. **Running Quality Checks**:
   - Run the unit test suite:
     ```bash
     uv run python -m unittest discover tests
     ```
   - Run linter checks:
     ```bash
     uv run --with ruff ruff check .
     ```
   - Run type checking:
     ```bash
     uv run --with mypy --with types-PyYAML mypy src
     ```

## Code Guidelines

- **Architecture Integrity**: Keep the gatekeeper, auditors, and CLI decoupled.
- **Typing**: All new Python code must be strictly typed and pass `mypy`.
- **Testing**: Add unit tests in `tests/` for any new audit rules, phase transitions, or gate checks.
- **Git Commit Messages**: Follow Conventional Commits format (e.g. `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`).

## Pull Request Process

1. Create a feature branch from `main`.
2. Ensure all tests, linter, and type checks pass.
3. Submit a pull request with a clear description of changes and motivation.
4. Maintainers will review your PR following our Stage-Gated SDD principles.
