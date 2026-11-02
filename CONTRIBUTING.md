# Contributing to PULSE

We welcome research contributions, clinical evaluation feedback, and dataset adapters.

## Development Workflow
1. Clone the repository and install dependencies via `pip install -r backend/requirements.txt`.
2. Follow PEP 8 style guidelines for Python code.
3. Verify test coverage using `pytest tests/`.
4. Run frontend checks using `npm run build` in `frontend/`.

## Pull Request Guidelines
- Ensure all tests pass.
- Maintain character offset fidelity for clinical span annotations.
- Include unit tests for any new clinical rule extractors.
