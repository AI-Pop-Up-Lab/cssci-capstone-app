# OLD STARTUP COMMAND THAT EXISTED FOR AZURE + GITHUB ACTIONS CONTINUOUS DEPLOYMENT.
# now docker is used so the requirements are in the docker image

#!/bin/bash
# pip install -r requirements.txt
# gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app --timeout 120 --threads 12