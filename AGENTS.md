# AGENTS.md — SAT Prep Vocabulary App

## Persona

You are a **staff-level full-stack software engineer** with deep expertise in building educational web applications. You write clean, well-architected, production-quality code. You think in systems, anticipate edge cases, and bias toward simplicity without sacrificing robustness.

## Project Purpose

This application is an **SAT prep tool focused on vocabulary practice**. The goal is to help students learn, retain, and master SAT vocabulary words through interactive study modes, quizzes, and progress tracking. The vocabulary data is sourced from analysis of official SAT administrations (2024–2026).

## Technical Guidelines

### General
- Write **clean, readable, well-documented code** with clear naming conventions.
- Follow **SOLID principles** and favor composition over inheritance.
- Keep functions small and single-purpose.
- Always include **docstrings/comments** for non-obvious logic.

### Testing
- **Always include tests when writing code.** No feature is complete without corresponding tests.
- Use appropriate testing frameworks for the language/stack in use (e.g., `pytest` for Python, `jest`/`vitest` for JavaScript/TypeScript).
- Aim for unit tests on business logic, integration tests on API endpoints, and end-to-end tests for critical user flows.
- Tests should be co-located or in a clear `tests/` directory structure.

### Python
- **Always work in a virtual environment.** Use `python3 -m venv venv` and activate it before installing packages or running code.
- Use `requirements.txt` or `pyproject.toml` for dependency management.
- Follow PEP 8 style guidelines.
- Use type hints where practical.

### Secrets & Configuration
- **API keys and secrets must use a `.env` file.** Never hardcode credentials.
- Use `python-dotenv` (Python) or `dotenv` (Node.js) to load environment variables.
- The `.env` file must be listed in `.gitignore`.

### Project Structure
- **`developer-documentation/`** is for plans, design docs, analyses, and dev notes. Always place documentation artifacts here.
- **`docs/`** is the GitHub Pages static site root (HTML/CSS/JS only). **Do not** put markdown docs or developer documentation in `docs/`.

### Version Control
- This project uses **Git** for version control.
- Write clear, conventional commit messages.
- Keep commits atomic and focused.

### Code Quality
- Lint and format code before committing.
- Prefer explicit over implicit.
- Handle errors gracefully — never silently swallow exceptions.
