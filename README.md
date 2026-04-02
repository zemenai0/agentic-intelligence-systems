# Agentic Intelligence Systems

Repository scaffold for an agentic AI systems project.

## Scope

This repository currently contains project structure only:

- packaging and project metadata
- source package folders and placeholder modules
- tests, evals, scripts, docs, and notebooks directories
- Docker, GitHub Actions, and pre-commit scaffolding

No application logic has been implemented in the package modules yet.

## Python Baseline

This scaffold targets Python 3.12.3.

## Quick Start

```bash
python3.12.3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
pip install -e .
pre-commit install
```

## Package Naming

The repository name uses hyphens, but the Python package uses underscores:

```python
import agentic_intelligence_systems
```

The requested `src/agentic-inteligence-systems/` path was normalized to
`src/agentic_intelligence_systems/` because Python package directories cannot
use hyphens.
