#!/bin/bash
pip install -r requirements.txt
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --timeout 0 # timeout is set to 0 to prevent gunicorn from killing workers that are taking a long time to generate biographies/responses, will be removed once streaming responses is added.