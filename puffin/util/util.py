from typing import TypeVar


def intify(data : str|int) -> str|int:
    if isinstance(data, str):
        return int(data) if data.isdigit() else data
    elif isinstance(data, int):
        return data
    else:
        raise ValueError('Expected string or int')