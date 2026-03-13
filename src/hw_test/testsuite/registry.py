from typing import Dict, Type
from .base import Test

REGISTRY: Dict[str, Type[Test]] = {}

def register(test_cls: Type[Test]):
    REGISTRY[test_cls.name] = test_cls
    return test_cls
