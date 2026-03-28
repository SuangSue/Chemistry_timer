# utils/config.py - 配置管理模块
import os, json
from pathlib import Path

APP_NAME = 'ClassroomTimer'

def get_config_dir() -> Path:
    base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    (d / 'rosters').mkdir(exist_ok=True)
    (d / 'logs').mkdir(exist_ok=True)
    (d / 'automation').mkdir(exist_ok=True)
    return d

CONFIG_FILE = get_config_dir() / 'config.json'

DEFAULTS = {
    'night_mode':    False,
    'opacity':       95,
    'anim_speed':    250,
    'silent_start':  False,
    'last_roster':   '',
    'custom_pick_n': 5,
    'always_on_top': True,
    'roster_password': '123123',
    'pick_speed': 0,
    'last_roster': '',
}

_cache: dict = {}

def load() -> dict:
    global _cache
    if _cache: return _cache
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _cache = {**DEFAULTS, **data}
    except Exception:
        _cache = dict(DEFAULTS)
    return _cache

def save(data: dict = None):
    global _cache
    if data is not None:
        _cache.update(data)
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'Config save error: {e}')

def get(key: str, default=None):
    return load().get(key, default if default is not None else DEFAULTS.get(key))

def set(key: str, value):
    load()
    _cache[key] = value
    save()

def get_config_dir_path() -> str:
    return str(get_config_dir())

def rosters_dir() -> Path:
    return get_config_dir() / 'rosters'

def list_rosters() -> list:
    d = rosters_dir()
    return [f.stem for f in sorted(d.glob('*.json')) if not f.stem.startswith('_')]

def load_roster(name: str) -> list:
    p = rosters_dir() / f'{name}.json'
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_roster(name: str, names: list):
    p = rosters_dir() / f'{name}.json'
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(names, f, ensure_ascii=False, indent=2)
    set('last_roster', name)

def load_pick_weights(roster_name: str) -> dict:
    """加载抽签权重，返回 {name: weight} 字典"""
    p = rosters_dir() / f'_weights_{roster_name}.json'
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_pick_weights(roster_name: str, weights: dict):
    p = rosters_dir() / f'_weights_{roster_name}.json'
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(weights, f, ensure_ascii=False, indent=2)

def load_pick_history(roster_name: str) -> list:
    """加载抽签历史记录"""
    p = rosters_dir() / f'_history_{roster_name}.json'
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_pick_history(roster_name: str, history: list):
    p = rosters_dir() / f'_history_{roster_name}.json'
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
