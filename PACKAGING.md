# Python Utilities - Packaging & Distribution Guide

Complete instructions for building, testing, and publishing this Python package following PyPA standards.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Development Setup](#development-setup)
4. [Building the Package](#building-the-package)
5. [Testing the Distribution](#testing-the-distribution)
6. [Publishing to PyPI](#publishing-to-pypi)
7. [Version Management](#version-management)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This package follows modern Python packaging standards:

- **PEP 621**: Project metadata in `pyproject.toml`
- **PEP 517/518**: Build system specification (Hatchling)
- **src/ layout**: Recommended package structure
- **Type hints**: PEP 561 compliant with `py.typed` marker

### Why These Standards?

- ✅ **PEP 621** eliminates `setup.py` and `setup.cfg` confusion
- ✅ **src/ layout** prevents accidentally importing from source during tests
- ✅ **Hatchling** provides faster, simpler builds than setuptools
- ✅ **pyproject.toml** is the single source of truth

---

## Prerequisites

### Required Tools

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install build tools
pip install build twine

# Optional: Install packaging tools
pip install setuptools wheel
```

### Python Version

Requires **Python 3.8 or higher**. Check your version:

```bash
python --version
```

---

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/python-utilities.git
cd python-utilities
```

### 2. Create Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source venv/bin/activate
```

### 3. Install in Editable Mode

```bash
# Install with all dev dependencies
pip install -e ".[dev]"

# Verify installation
python -c "from python_utilities import FileUtils; print('Success!')"
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=utilities --cov-report=html

# Run specific module tests
pytest tests/test_file_utils.py -v
```

---

## Building the Package

### Step 1: Clean Previous Builds

```bash
# Remove old distributions
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force src\*.egg-info -ErrorAction SilentlyContinue
```

### Step 2: Run Pre-Build Checks

```bash
# Run tests
pytest

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

### Step 3: Build Distributions

```bash
# Build both sdist and wheel
python -m build
```

**Output**:
- `dist/python_utilities-1.0.0.tar.gz` - Source distribution
- `dist/python_utilities-1.0.0-py3-none-any.whl` - Wheel (built distribution)

### Step 4: Verify Build Contents

```bash
# List wheel contents
python -m zipfile -l dist/utilities-1.0.0-py3-none-any.whl

# Check for required files
python -m zipfile -l dist/utilities-1.0.0-py3-none-any.whl | Select-String "py.typed"
```

**What to check**:
- ✅ All Python modules present
- ✅ `py.typed` marker included
- ✅ No test files in distribution
- ✅ Correct package structure

---

## Testing the Distribution

### Test Installation from Wheel

```bash
# Create test environment
python -m venv test_env
.\test_env\Scripts\Activate.ps1

# Install from wheel
pip install dist/utilities-1.0.0-py3-none-any.whl

# Test imports
python -c "from python_utilities import FileUtils, RestClient; print('✓ Imports work')"

# Test functionality
python -c "from python_utilities import FileUtils; fu = FileUtils(); print('✓ FileUtils works')"

# Clean up
deactivate
Remove-Item -Recurse test_env
```

### Check Package Metadata

```bash
# Install twine if not already
pip install twine

# Check distributions
twine check dist/*
```

**Twine checks**:
- ✅ README renders correctly on PyPI
- ✅ Metadata is valid
- ✅ No rendering warnings

---

## Publishing to PyPI

### Prerequisites

1. **Create PyPI accounts**:
   - [TestPyPI](https://test.pypi.org/account/register/) (for testing)
   - [PyPI](https://pypi.org/account/register/) (for production)

2. **Create API tokens**:
   - [TestPyPI Tokens](https://test.pypi.org/manage/account/#api-tokens)
   - [PyPI Tokens](https://pypi.org/manage/account/#api-tokens)

3. **Configure `.pypirc`** (optional but recommended):

```bash
# Windows: %USERPROFILE%\.pypirc
# macOS/Linux: ~/.pypirc
```

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...

[testpypi]
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZw...
```

### Step 1: Upload to TestPyPI (RECOMMENDED FIRST)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# You'll be prompted for credentials if not using .pypirc
```

### Step 2: Test Installation from TestPyPI

```bash
# Create test environment
python -m venv test_testpypi
.\test_testpypi\Scripts\Activate.ps1

# Install from TestPyPI (use real PyPI for dependencies)
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ python-utilities

# Test it
python -c "from python_utilities import FileUtils; print('✓ Works from TestPyPI')"

# Clean up
deactivate
Remove-Item -Recurse test_testpypi
```

### Step 3: Upload to PyPI (Production)

```bash
# Upload to real PyPI
twine upload dist/*
```

### Step 4: Verify on PyPI

Visit: https://pypi.org/project/python-utilities/

Check:
- ✅ README displays correctly
- ✅ Version number is correct
- ✅ Dependencies listed
- ✅ Project URLs work
- ✅ Classifiers accurate

### Step 5: Test Final Installation

```bash
# Install from PyPI
pip install python-utilities

# Test
python -c "from python_utilities import FileUtils; print('✓ Published successfully')"
```

---

## Version Management

### Semantic Versioning

Follow [SemVer](https://semver.org/): **MAJOR.MINOR.PATCH**

- **MAJOR**: Breaking changes (1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, backward compatible (1.0.0 → 1.0.1)

### Updating Version

Edit `pyproject.toml`:

```toml
[project]
version = "1.1.0"  # Update here
```

Also update `src/python_utilities/__init__.py`:

```python
__version__ = "1.1.0"  # Keep in sync
```

### Release Checklist

Before each release:

1. ✅ Update version in `pyproject.toml`
2. ✅ Update version in `src/python_utilities/__init__.py`
3. ✅ Update `CHANGELOG.md` (if you create one)
4. ✅ Run full test suite: `pytest`
5. ✅ Check code quality: `ruff check && mypy src/`
6. ✅ Clean and rebuild: `python -m build`
7. ✅ Check with twine: `twine check dist/*`
8. ✅ Test on TestPyPI first
9. ✅ Tag in Git: `git tag v1.1.0 && git push --tags`
10. ✅ Upload to PyPI

---

## Troubleshooting

### Common Issues

#### "Module not found" after installation

**Solution**: Ensure you're using the package name correctly:
```python
from python_utilities import FileUtils  # Correct
from python-utilities import FileUtils  # Wrong (hyphens)
```

#### "Package already exists" on PyPI

Once uploaded, you **cannot replace** a version.

**Solution**:
1. Increment version number
2. Rebuild: `python -m build`
3. Upload new version

#### Tests fail after installation

**Cause**: Tests importing from source instead of installed package.

**Solution**: The src/ layout (already implemented) prevents this.

#### Import errors in editable mode

**Solution**:
```bash
pip install -e . --force-reinstall --no-deps
```

#### Twine upload fails with "Invalid credentials"

**Solution**:
- Use API tokens, not passwords
- Ensure `.pypirc` is properly formatted
- Check token hasn't expired

### Getting Help

- **PyPA Discourse**: https://discuss.python.org/c/packaging/
- **Packaging Guide**: https://packaging.python.org/
- **This repo's issues**: https://github.com/yourusername/python-utilities/issues

---

## Advanced Topics

### Using setuptools Instead of Hatchling

If you prefer setuptools:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

### Dynamic Versioning from Git

Use `hatch-vcs` for git-based versioning:

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]

[tool.hatch.version]
source = "vcs"
```

### Building Only Specific Distributions

```bash
# Build only wheel
python -m build --wheel

# Build only source distribution
python -m build --sdist
```

### Including Data Files

In `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel.shared-data]
"data" = "share/python_utilities/data"
```

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine
      
      - name: Build package
        run: python -m build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

---

## Summary

This package demonstrates modern Python packaging:

1. **pyproject.toml** - Single configuration file (PEP 621)
2. **src/ layout** - Best practice structure
3. **Hatchling** - Modern build backend
4. **Type hints** - With py.typed marker
5. **pytest** - Modern testing
6. **Ruff** - Fast linting
7. **TestPyPI → PyPI** - Safe deployment

By following these practices, your package is:
- ✅ Standards-compliant
- ✅ Easy to maintain
- ✅ Ready for production
- ✅ Compatible with modern tooling

---

**Questions?** Check the [Python Packaging User Guide](https://packaging.python.org/) or open an issue.
