#!/usr/bin/env bash
pkg update -y
pkg install python -y
pkg install python-pillow -y
pip install --upgrade rich
pip install -r requirements.txt
