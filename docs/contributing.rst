Contributing Guide
===================

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

Development Setup
-----------------

1. **Clone the repository:**

   .. code-block:: bash

      git clone https://github.com/your-org/google-photos-icloud-migration.git
      cd google-photos-icloud-migration

2. **Install development dependencies:**

   .. code-block:: bash

      pip install -r requirements-dev.txt

3. **Set up pre-commit hooks:**

   .. code-block:: bash

      pre-commit install

4. **Verify setup:**

   .. code-block:: bash

      make help
      make test

Code Style
----------

We follow PEP 8 with modifications:

* **Line length**: 100 characters (Black default)
* **Formatting**: Use Black for automatic formatting
* **Import sorting**: Use isort with Black profile
* **Type hints**: Use type hints for all function signatures

Before committing, format your code:

.. code-block:: bash

   make format
   # or
   black .
   isort .

Testing
-------

Run tests with:

.. code-block:: bash

   make test
   # or
   pytest

Run with coverage:

.. code-block:: bash

   make test-cov
   # or
   pytest --cov=. --cov-report=html

Writing Tests
-------------

* Place tests in the ``tests/`` directory
* Name test files ``test_*.py``
* Use descriptive test function names starting with ``test_``
* Follow existing test patterns

Pull Request Process
--------------------

1. Create a branch: ``git checkout -b feature/your-feature-name``
2. Make your changes
3. Run checks: ``make format lint type-check test``
4. Commit with clear messages
5. Push and create a Pull Request

For more details, see ``CONTRIBUTING.md`` in the repository root.
