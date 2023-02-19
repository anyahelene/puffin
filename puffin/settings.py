import regex

DEBUG = True
DB_URL = "sqlite+pysqlite:///run/db.sqlite"

__VALID_DISPLAY_NAME_CHARS__ = r'[\p{print}]'
__VALID_SLUG_CHARS__ = r'[a-z0-9-]'


###########################################################################################
VALID_DISPLAY_NAME_REGEX = regex.compile(f'^{__VALID_DISPLAY_NAME_CHARS__}+$')
VALID_DISPLAY_NAME_PREFIX = regex.compile(f'^{__VALID_DISPLAY_NAME_CHARS__}+')
VALID_SLUG_REGEX = regex.compile(f'^{__VALID_SLUG_CHARS__}+$')
VALID_SLUG_PREFIX = regex.compile(f'^{__VALID_SLUG_CHARS__}+')