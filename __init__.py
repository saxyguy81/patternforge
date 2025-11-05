"""
PatternForge: Fast, deterministic glob-pattern discovery for hierarchical data.

This package provides automatic wildcard pattern discovery for matching structured
and hierarchical data with zero false positives (EXACT mode).

Quick Start:
    >>> # Add src/ to your PYTHONPATH or use: sys.path.insert(0, 'src')
    >>> from patternforge import propose_solution, SolveOptions
    >>>
    >>> include = ["alpha/module1/mem", "alpha/module2/io"]
    >>> exclude = ["gamma/module1/mem"]
    >>>
    >>> solution = propose_solution(include, exclude, SolveOptions())
    >>> print(solution['raw_expr'])  # e.g., 'alpha/*'

For comprehensive documentation, see:
    - USER_GUIDE.md: Complete user guide with examples
    - STRUCTURED_SOLVER_GUIDE.md: Multi-field pattern matching
    - examples/: Runnable example scripts
"""

__version__ = "1.0.0"
__author__ = "PatternForge Contributors"

# This top-level __init__.py marks the repository as a package.
# The actual implementation is in src/patternforge/
#
# To use PatternForge, add src/ to your PYTHONPATH:
#   export PYTHONPATH=/path/to/patternforge/src:$PYTHONPATH
#
# Or in Python:
#   import sys
#   sys.path.insert(0, '/path/to/patternforge/src')
#   from patternforge import propose_solution

__all__ = [
    "__version__",
    "__author__",
]


