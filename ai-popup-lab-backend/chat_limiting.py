import time
import json
from pathlib import Path


# path for json files (on mounted files in deployment)
ip_requests_path = '/mnt/data/day_ip_requests.json'
active_request_users_path = '/mnt/data/users_request_active.json'

# path for json files in dev
# base_dir = Path(__file__).resolve().parent  # goes up from file to ai-popup-lab-backend (backend root)
# ip_requests_path = base_dir / "user_limiting" / "day_ip_requests.json"
# active_request_users_path = base_dir / "user_limiting" / "users_request_active.json"

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

    with open(ip_requests_path, 'r') as f:
        ip_requests = json.load(f)

    if ip in ip_requests:
        if ip_requests[ip] == daily_request_limit:
            ip_limited = True
        else:
            ip_requests[ip] += 1

    else:
        ip_requests[ip] = 1

    with open(ip_requests_path, "w") as f:
        json.dump(ip_requests, f, indent=4)

    return ip_limited

# functions to add user/ip to a list that stops a request being processed if they already have one in action, this is because the code that exists which stops a user sending a message when waiting for the response is client side, thus can be bypassed with changing client side code. this means that regardless, calls cannot be spammed
def add_or_remove_user_requestlist(add_or_remove, ip):

    with open(active_request_users_path, 'r') as f:
        active_user_requests_ips = json.load(f)

    ongoing_request_ips = active_user_requests_ips["users"]

    if add_or_remove.lower() == "add":

        ongoing_request_ips.append(ip)

    elif add_or_remove.lower() == "remove":
        ongoing_request_ips.remove(ip)
    else:
        return ValueError


    with open(active_request_users_path, "w") as f:
        json.dump({"users": ongoing_request_ips}, f, indent=4)

def check_if_user_ongoing_request(ip):

    ongoing_request = False

    with open(active_request_users_path, 'r') as f:
        active_user_requests_ips = json.load(f)

    ongoing_request_ips = active_user_requests_ips["users"]

    if ip in ongoing_request_ips:
        ongoing_request = True

    return ongoing_request