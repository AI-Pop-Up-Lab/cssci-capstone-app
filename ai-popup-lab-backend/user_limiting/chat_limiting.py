import time
import json
from pathlib import Path
from dotenv import load_dotenv
import os
import threading

load_dotenv()
ENV = os.getenv("ENV")

if ENV == "development":
    # path for json files in dev
    base_dir = Path(__file__).resolve().parent  # goes up from file to folder it is in, user_limiting
    ip_requests_path = base_dir / "day_ip_requests.json"
    active_request_users_path = base_dir / "users_request_active.json"
else:
    # path for json files (on mounted files in deployment)
    ip_requests_path = '/mnt/data/day_ip_requests.json'
    active_request_users_path = '/mnt/data/users_request_active.json'

_lock = threading.Lock()  # single lock for all file operations

def response_friction(friction_time_secs):

    time.sleep(friction_time_secs)
    return

def check_if_ip_limited(ip):

    # disregard development calls
    if ip == 'dev-ip':
        return False

    # limit for requests / day
    daily_request_limit = 25

    ip_limited = False

    with _lock:
        with open(ip_requests_path, 'r+') as f:
            ip_requests = json.load(f)

            if ip in ip_requests:
                if ip_requests[ip] >= daily_request_limit:
                    ip_limited = True
                else:
                    ip_requests[ip] += 1

            else:
                ip_requests[ip] = 1

            f.seek(0)
            f.truncate()
            json.dump(ip_requests, f, indent=4)

    return ip_limited

# functions to add user/ip to a list that stops a request being processed if they already have one in action, this is because the code that exists which stops a user sending a message when waiting for the response is client side, thus can be bypassed with changing client side code. this means that regardless, calls cannot be spammed
def add_or_remove_user_requestlist(add_or_remove, ip):

    with _lock:
        with open(active_request_users_path, 'r+') as f:
            active_user_requests_ips = json.load(f)
            ongoing_request_ips = active_user_requests_ips["users"]

            if add_or_remove.lower() == "add":
                ongoing_request_ips.append(ip)
            elif add_or_remove.lower() == "remove":
                if ip in ongoing_request_ips:
                    ongoing_request_ips.remove(ip)
            else:
                raise ValueError("add_or_remove must be 'add' or 'remove'")

            f.seek(0)
            f.truncate()
            json.dump({"users": ongoing_request_ips}, f, indent=4)

def check_if_user_ongoing_request(ip):

    with _lock:
        with open(active_request_users_path, 'r') as f:
            active_user_requests_ips = json.load(f)

    return ip in active_user_requests_ips["users"]