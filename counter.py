import json, os, threading

COUNTER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'counter.json')
_lock = threading.Lock()

def get_next():
    with _lock:
        try:
            with open(COUNTER_FILE, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {'counter': 0}
        data['counter'] += 1
        with open(COUNTER_FILE, 'w') as f:
            json.dump(data, f)
        return data['counter']

def current():
    try:
        with open(COUNTER_FILE, 'r') as f:
            return json.load(f).get('counter', 0)
    except:
        return 0
