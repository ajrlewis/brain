# Python Preset

Adopted for Brain. Target Python 3.13 or newer, with explicit types and provider-independent domain code. The workspace currently selects Python 3.13.15.

- Follow the Python version, packaging layout, formatter, linter, and test runner already present.
- Prefer typed, small modules with explicit boundaries over broad utility modules.
- Keep environment-dependent configuration outside import-time side effects.
- Validate external inputs at service boundaries. Pydantic is a reasonable default for structured external data and settings when the project has not adopted another validator; ordinary type hints do not perform runtime validation.
- Prefer normal typed Python objects for trusted internal data when runtime validation adds no value.
- Add focused tests around behavior changes.
- Record canonical commands in `.agents/COMMANDS.md`.
