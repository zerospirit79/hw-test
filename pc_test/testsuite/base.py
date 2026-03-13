from typing import Any, Dict

class Test:
    name = "base"
    timeout = 300
    def run(self, ctx: Dict[str,Any]) -> Dict[str,Any]:
        raise NotImplementedError
