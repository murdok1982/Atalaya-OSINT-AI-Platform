from enum import Enum

class ClassificationLevel(Enum):
    UNCLASSIFIED = 0
    CONFIDENTIAL = 1
    SECRET = 2
    TOP_SECRET = 3

def enforce_classification(user_level: int, resource_level: int):
    if user_level < resource_level:
        raise PermissionError("Nivel de autorización insuficiente")
