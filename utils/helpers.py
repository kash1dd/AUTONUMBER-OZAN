import json
import os

CONFIG_FILE = "config/config.json"
API_KEYS_FILE = "config/api_keys.json"
HISTORY_FILE = "config/history.json"
STATISTICS_FILE = "config/statistics.json"

DEFAULT_CONFIG = {
    "api_urls": {
        "tiger": "https://api.tiger-sms.com/stubs/handler_api.php",
        "reg": "https://reg-sms.org/stubs/handler_api.php",
        "smslive": "https://api.smslive.pro/stubs/handler_api.php"
    },
    "service_id": "aic",
    "country_id": "62",
    "sms_wait_timeout": 90,
    "auto_copy": {"phone": True, "code": True},
    "sound_notifications": {"enabled": True, "volume": 50},
    "low_balance_warning": 10.0
}

DEFAULT_STATISTICS = {
    "purchases": {"tiger": 0, "reg": 0, "smslive": 0},
    "codes": {"tiger": 0, "reg": 0, "smslive": 0},
    "total_spent": {"tiger": 0.0, "reg": 0.0, "smslive": 0.0},
    "last_balance": {"tiger": 0.0, "reg": 0.0, "smslive": 0.0},
    "waiting_times": {"total_seconds": 0, "count": 0}
}

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def load_api_keys():
    try:
        with open(API_KEYS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"tiger": "", "reg": "", "smslive": ""}

def save_api_keys(keys):
    os.makedirs(os.path.dirname(API_KEYS_FILE), exist_ok=True)
    with open(API_KEYS_FILE, "w") as f:
        json.dump(keys, f)

def load_history():
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def add_to_history(entry):
    history = load_history()
    history.append(entry)
    save_history(history)

def load_statistics():
    try:
        with open(STATISTICS_FILE, "r") as f:
            stats = json.load(f)
            for key, value in DEFAULT_STATISTICS.items():
                stats.setdefault(key, value)
                if isinstance(value, dict):
                    stats[key].update({k: v for k, v in value.items() if k not in stats[key]})
            return stats
    except FileNotFoundError:
        return DEFAULT_STATISTICS.copy()

def save_statistics(stats):
    os.makedirs(os.path.dirname(STATISTICS_FILE), exist_ok=True)
    with open(STATISTICS_FILE, "w") as f:
        json.dump(stats, f, indent=4)

def update_statistics(stat_type, service, value=None):
    stats = load_statistics()
    if stat_type == "purchase":
        stats["purchases"][service] += 1
    elif stat_type == "code":
        stats["codes"][service] += 1
    elif stat_type == "spent" and value:
        stats["total_spent"][service] += value
    elif stat_type == "balance" and value:
        stats["last_balance"][service] = value
    elif stat_type == "waiting_time" and value:
        stats["waiting_times"]["total_seconds"] += value
        stats["waiting_times"]["count"] += 1
    save_statistics(stats)
    return stats