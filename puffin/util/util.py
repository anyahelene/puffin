from datetime import datetime, date, time, timezone
from typing import Any, TypeVar
import regex
import json
class DateEncoder(json.JSONEncoder):
    def default(self,obj):
        if isinstance(obj, datetime) or isinstance(obj, date) or isinstance(obj, time):
            return obj.isoformat().replace('+00:00','Z')
        return json.JSONEncoder.default(self, obj)
    
def intify(data : str|int) -> str|int:
    if isinstance(data, str):
        return int(data) if data.isdigit() else data
    elif isinstance(data, int):
        return data
    else:
        raise ValueError('Expected string or int')

def now() -> datetime:
    return datetime.now(timezone.utc)

def decode_date(s:str) -> datetime|None:
    try:
        if not s:
            return None
        elif s.endswith('Z'):
            return datetime.fromisoformat(s[:-1] + '+00:00')
        else:
            return datetime.fromisoformat(s)
    except:
        return None
    

__VALID_DISPLAY_NAME_CHARS__ = r'[\p{print}]'
__VALID_SLUG_CHARS__ = r'[a-z0-9-]'
__VALID_SLUG_PATH_CHARS__ = r'[/a-z0-9-]'
GITLAB_PATH_RE = '([a-zA-Z0-9_\\.][a-zA-Z0-9_\\-\\.]*[a-zA-Z0-9_\\-]|[a-zA-Z0-9_])';

VALID_DISPLAY_NAME_REGEX : Any = regex.compile(f'^{__VALID_DISPLAY_NAME_CHARS__}+$')
VALID_DISPLAY_NAME_PREFIX : Any = regex.compile(f'^{__VALID_DISPLAY_NAME_CHARS__}+')
VALID_SLUG_REGEX : Any = regex.compile(f'^{GITLAB_PATH_RE}$')
VALID_SLUG_PREFIX : Any = regex.compile(f'^{__VALID_SLUG_CHARS__}+')
VALID_SLUG_PATH_REGEX : Any =          regex.compile(f'^{GITLAB_PATH_RE}(/{GITLAB_PATH_RE})*$')
VALID_SLUG_PATH_OR_EMPTY_REGEX : Any = regex.compile(f'^({GITLAB_PATH_RE}(/{GITLAB_PATH_RE})*)?$')
VALID_SLUG_PATH_PREFIX : Any = regex.compile(f'^{__VALID_SLUG_PATH_CHARS__}+')