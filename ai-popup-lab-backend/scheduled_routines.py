# file for scheduled routines
# daily reset of IP request limits
# weekly sample generation

import json
from pathlib import Path
from data_generation.generate_data import generate_data


# path for json files (on mounted files in deployment)
# ip_requests_path = '/mnt/data/day_ip_requests.json'

# path for json files in dev
base_dir = Path(__file__).resolve().parent  # goes up from file to ai-popup-lab-backend (backend root)
ip_requests_path = base_dir / "user_limiting" / "day_ip_requests.json"


def weekly_data_generation():
    generate_data()

def reset_ip_request_limits():

    # reset ip request limit json
    with open(ip_requests_path, "w") as f:
        json.dump({}, f, indent=4)