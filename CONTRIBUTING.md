# Contributing to Policy Pilot

Thank you for your interest in contributing! This document provides guidelines and instructions.

## Code of Conduct

- Be respectful and inclusive
- Focus on the code, not the person
- Help others learn and grow
- Report issues professionally

## Getting Started

### 1. Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/PolicyPilot.git
cd PolicyPilot
```

### 2. Set Up Development Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .  # Install in editable mode
```

### 3. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

## Development Guidelines

### Code Style
- Use **Black** for formatting: `black chatbot.py web_app.py`
- Follow **PEP 8** conventions
- Type hints required for all functions
- Meaningful variable names (no `x`, `y`, `data1`, etc.)

### Testing
- Write tests for new features in `tests/`
- Run tests before committing: `pytest tests/ -v`
- Aim for >90% code coverage
- Test edge cases and error conditions

### Docstrings
- Use Google-style docstrings
- Include parameters, return types, and examples
- Document exceptions raised

Example:
```python
def retrieve_chunks(query: str, top_k: int = 3) -> list[dict]:
    """Retrieve relevant document chunks using semantic search.
    
    Args:
        query: The user query string
        top_k: Number of chunks to retrieve (default: 3)
        
    Returns:
        List of dictionaries with 'id', 'source', and 'text' keys.
        
    Raises:
        FileNotFoundError: If FAISS index not found.
        ValueError: If top_k < 1.
    """
```

### Commit Messages
- Use clear, descriptive messages
- Format: `[TYPE] Brief description`
- Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`

Examples:
```
[feat] Add streaming response support
[fix] Handle missing PDFs gracefully
[docs] Update setup instructions
[test] Add edge case tests for chunking
```

## Common Tasks

### Adding a New Feature
1. Create feature branch: `git checkout -b feature/new-feature`
2. Implement with tests
3. Update documentation
4. Submit PR with description

### Fixing a Bug
1. Create issue describing the bug
2. Create branch: `git checkout -b fix/bug-description`
3. Add test that reproduces the bug
4. Fix the bug
5. Submit PR referencing the issue

### Improving Documentation
- Update README.md for user-facing changes
- Update module docstrings for code changes
- Add examples for new features
- Check for typos and clarity

## Pull Request Process

1. **Update your branch**: `git pull origin main`
2. **Run tests**: `pytest tests/ -v`
3. **Format code**: `black .`
4. **Commit changes**: `git commit -m "[type] message"`
5. **Push**: `git push origin feature/your-feature`
6. **Create PR** on GitHub with:
   - Clear title and description
   - Reference to related issues
   - Summary of changes
   - Testing performed

## Before Submitting

- [ ] Tests pass: `pytest tests/ -v`
- [ ] Code formatted: `black .`
- [ ] Docstrings added
- [ ] No breaking changes (or documented)
- [ ] README updated if needed
- [ ] Commit messages clear

## Questions?

- Check existing issues and discussions
- Create a new discussion for questions
- Email: maintainer@example.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for making Policy Pilot better! 🚀
