# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Google Photos to iCloud Migration'
copyright = '2024, Google Photos iCloud Migration Contributors'
author = 'Google Photos iCloud Migration Contributors'
release = '1.0.0'
version = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',  # For Google/NumPy style docstrings
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'myst_parser',  # For Markdown support (optional)
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'  # Read the Docs theme (recommended)
# Alternative themes:
# html_theme = 'alabaster'  # Default theme
# html_theme = 'sphinx_book_theme'  # Modern theme
# html_theme = 'furo'  # Minimal theme

html_static_path = ['_static']
html_logo = None  # Add logo path if available
html_favicon = None  # Add favicon path if available

# -- Extension configuration -------------------------------------------------

# Napoleon settings for docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pathlib': ('https://docs.python.org/3/library/pathlib.html', None),
}

# Todo extension
todo_include_todos = True

# -- Custom configuration ---------------------------------------------------

# Path to source code for autodoc
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
