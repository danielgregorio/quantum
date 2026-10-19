"""The Hive lab as an MCP server: an agent drives the Hive through tools.

    python os/scripts/lab/hive_mcp.py            # over stdio, as .mcp.json at the repository's root declares it
    python os/scripts/lab/hive_mcp.py --selftest # a crash, an offer, an approval: no MCP client needed

The tools wrap hive-lab (os/crates/hive-lab), which runs the real hive-cortex and
hive-synapse and plays the nerves, the actuator, grove and the dashboard; it can also run
the real dashboard and grove in a pseudo-terminal and read their screens as text. The lab
needs root (its users live in a private mount namespace): the server runs it with
`sudo -n` when it is not root. It builds the workspace first if the binaries are missing.
Needs the `mcp` package for the server itself (pip install mcp); --selftest does not.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

OS_DIR = Path(__file__).resolve().parents[2]
TAPES = OS_DIR / 'crates' / 'hive-lab' / 'tapes'
DRIVER = OS_DIR / 'target' / 'debug' / 'hive-lab'

INSTRUCTIONS = """Drive the Hive of Quantum OS (os/ in this repository) without a VM.

hive_start starts the real hive-cortex and hive-synapse, and the roles the lab plays: a nerve, the
actuator (which records every action and runs none), grove and the dashboard. hive_request sends one
lab request and answers it; the ops:
- what the system did, from a nerve: {"op":"crash","service":"nginx.service","exit_code":1,"restarts":5},
  {"op":"port_conflict","port":80,"requested_by":"app","held_by":"nginx"}, {"op":"disk_low","mount":"/","percent":96},
  {"op":"command","cmd":"rm -rf /srv"}, {"op":"inject","message":<any HiveMessage as JSON>};
- grove: {"op":"ask","text":"..."}, {"op":"not_found","command":"htop","package":"htop"}, {"op":"anonymous","on":true};
- the dashboard: {"op":"approve"} (the latest offer), {"op":"dismiss"};
- anything as any role: {"op":"send","as":"shell","message":...} (to see what a role may not do);
- waiting and checking: {"op":"observe"} (what each role received since the last look),
  {"op":"until","to":"actuator","type":"ActionRequest","contains":"nginx","excludes":"PACKAGE","timeout":5},
  {"op":"none","to":"actuator","within":1}, {"op":"log_until","daemon":"cortex","contains":"Rejecting"},
  {"op":"log","daemon":"synapse"};
- the real programs: {"op":"tui","app":"dashboard"} or "grove", then hive_view(app),
  {"op":"keys","app":"dashboard","keys":["Down","Enter"]}, {"op":"until_screen","app":"grove","contains":"..."}.
hive_tape saves the requests of this session as a tape in os/crates/hive-lab/tapes/, which CI plays.
hive_end stops the lab."""

# What a tape keeps: the requests that make or check a behaviour, not the looks.
NOT_TAPED = {'observe', 'view', 'log'}


class HiveLab:
    """One hive-lab driver process, one request line in, one answer line out."""

    def __init__(self) -> None:
        self.proc: Optional[subprocess.Popen] = None
        self.taped: List[dict] = []

    def _ensure_driver(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            return
        if not DRIVER.is_file() or not (DRIVER.parent / 'hive-cortex').is_file():
            subprocess.run(['cargo', 'build', '--workspace', '--quiet'], cwd=OS_DIR, check=True,
                           stdout=sys.stderr, stderr=sys.stderr)
        cmd = [str(DRIVER)]
        if os.geteuid() != 0:
            cmd = ['sudo', '-n', *cmd]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, bufsize=1)

    def request(self, req: dict) -> dict:
        self._ensure_driver()
        assert self.proc and self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(json.dumps(req) + '\n')
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('hive-lab stopped (as root? `sudo -n` needs no password)')
        answer = json.loads(line)
        if req.get('op') not in NOT_TAPED:
            self.taped.append(req)
        return answer

    def start(self, synapse: bool = True) -> dict:
        self.taped = []
        return self.request({'op': 'start', 'synapse': synapse})

    def tape(self, name: str, about: str) -> dict:
        if not self.taped:
            raise RuntimeError('nothing to tape: start the lab and send requests first')
        if not name.replace('-', '').isalnum():
            raise RuntimeError('name: letters, digits and dashes (it becomes <name>.jsonl)')
        lines = [f'// {about}'] + [json.dumps(r, ensure_ascii=False) for r in self.taped]
        if self.taped[-1].get('op') != 'end':
            lines.append('{"op":"end"}')
        path = TAPES / f'{name}.jsonl'
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return {'ok': True, 'tape': str(path.relative_to(OS_DIR.parent)), 'requests': len(lines) - 1}

    def end(self) -> dict:
        if self.proc is None or self.proc.poll() is not None:
            return {'ok': True}
        answer = self.request({'op': 'end'})
        assert self.proc.stdin
        self.proc.stdin.close()
        self.proc.wait(timeout=10)
        self.proc = None
        return answer


def build_server(lab: Optional[HiveLab] = None):
    from mcp.server.mcpserver import MCPServer

    lab = lab or HiveLab()
    server = MCPServer('hive-lab', instructions=INSTRUCTIONS)
    dump = lambda value: json.dumps(value, separators=(',', ':'), ensure_ascii=False)  # noqa: E731

    @server.tool()
    def hive_start(synapse: bool = True) -> str:
        """Starts the lab: the real hive-cortex and hive-synapse, and the nerve, actuator, grove and
        dashboard roles. Builds os/ first if needed. synapse=false leaves hive-synapse out."""
        return dump(lab.start(synapse))

    @server.tool()
    def hive_request(request: dict) -> str:
        """Sends one lab request ({"op": ...}, see the server's instructions) and answers it."""
        return dump(lab.request(request))

    @server.tool()
    def hive_view(app: str) -> str:
        """The screen of the real dashboard or grove (started with {"op":"tui","app":...}), as text."""
        answer = lab.request({'op': 'view', 'app': app})
        return answer.get('screen') or dump(answer)

    @server.tool()
    def hive_tape(name: str, about: str) -> str:
        """Saves this session's requests (not the looks) as os/crates/hive-lab/tapes/<name>.jsonl,
        with `about` as its first line: what behaviour the tape holds the Hive to. CI plays it."""
        return dump(lab.tape(name, about))

    @server.tool()
    def hive_end() -> str:
        """Stops the lab."""
        return dump(lab.end())

    return server


def selftest() -> int:
    lab = HiveLab()
    steps = [
        lab.start(),
        lab.request({'op': 'crash', 'service': 'nginx.service', 'exit_code': 1, 'restarts': 5}),
        lab.request({'op': 'until', 'to': 'dashboard', 'contains': 'Restart nginx', 'timeout': 10}),
        lab.request({'op': 'approve'}),
        lab.request({'op': 'until', 'to': 'actuator', 'type': 'ActionRequest'}),
        lab.end(),
    ]
    failed = [s for s in steps if not s.get('ok')]
    print('hive-lab selftest:', 'ok' if not failed else f'FAILED {failed}')
    return 1 if failed else 0


def main() -> int:
    if '--selftest' in sys.argv:
        return selftest()
    try:
        server = build_server()
    except ImportError:
        print('the Hive lab MCP server needs the mcp package: pip install mcp')
        return 1
    server.run('stdio')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
