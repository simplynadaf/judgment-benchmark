"""Pytest config: make the src/ layout importable without installing."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
