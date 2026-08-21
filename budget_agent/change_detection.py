from typing import Any, Dict, List


def detect_changes(previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, List[Any]]:
    changes: Dict[str, List[Any]] = {}
    keys = sorted(set(previous.keys()) | set(current.keys()))
    for key in keys:
        old = previous.get(key)
        new = current.get(key)
        if old != new:
            changes[key] = [old, new]
    return changes
