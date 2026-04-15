#!/bin/bash
pip install -r requirements.txt
gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app --timeout 120 --threads 12