"""Ensure the backend package root is importable when running pytest from here.

pytest inserts the directory containing the rootdir conftest.py onto sys.path,
so tests can `from app.main import app` without an editable install.
"""
