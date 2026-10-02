#!/bin/bash
set -e
PYTHONPATH=. coverage run --source=dota2cl ./runtests.py
coverage xml && coverage report