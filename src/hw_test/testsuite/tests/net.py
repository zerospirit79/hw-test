import subprocess
from ..registry import register
from ..base import Test

@register
class PingExternal(Test):
    name = "net.ping_external"
    def run(self, ctx):
        host = ctx.get("ping_host","8.8.8.8")
        p = subprocess.run(["ping","-c","3",host], capture_output=True, text=True)
        return {"ok": p.returncode == 0, "stdout": p.stdout, "stderr": p.stderr, "host": host}
