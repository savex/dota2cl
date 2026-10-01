#!/bin/bash
PYTHONPATH=. coverage run --source=dotclient ./runtests.py
coverage xml && coverage report