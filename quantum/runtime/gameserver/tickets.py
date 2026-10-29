"""The tickets of a world whose accounts are a site's (PLAN_GAME_SERVER.md, Phase 4: accounts="site").

The site, which knows its accounts and their passwords, gives a player who signs in a ticket: the account, the name it
shows and when the ticket ends, signed (HMAC-SHA256) with a secret the site and the world share. The game opens the
world's WebSocket with it (hello {"ticket": ...}); the world checks the signature and the time, and the player comes
in as that account, to its hero where it was. The world never sees a password, and never asks the site anything.

The secret is the environment's, QUANTUM_WORLD_SECRET on both machines: never a file of the repository, never in the
world's .q. A ticket lasts a minute by default: it is for coming in, not for staying; and it comes in once (the world
keeps the ones it took until they end), so a ticket overheard is a ticket spent.

    from quantum.runtime.gameserver.tickets import issue
    ticket = issue('ana@site', 'Ana', secret=os.environ['QUANTUM_WORLD_SECRET'])
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from typing import NamedTuple, Optional

SECRET_ENV = 'QUANTUM_WORLD_SECRET'
ACCOUNT = re.compile(r'^[A-Za-z0-9_.@+-]{1,64}$')     # the site's id of the account: the hero's is hero:<it>
MAX_NAME = 24


class TicketError(Exception):
    pass


class Ticket(NamedTuple):
    account: str
    name: str
    ends: int           # the second it ends (Unix time)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def secret_from_env() -> Optional[bytes]:
    value = os.environ.get(SECRET_ENV, '')
    return value.encode('utf-8') if len(value) >= 16 else None


def shown(name: object, account: str) -> str:
    """The name a hero shows: printable, 24 characters at most; the account's when there is none."""
    text = ''.join(c for c in str(name or '') if c.isprintable()).strip()[:MAX_NAME]
    return text or account[:MAX_NAME]


def issue(account: str, name: str, secret: str | bytes, seconds: float = 60.0, now: Optional[float] = None) -> str:
    """A ticket for the account, shown as name, good for so many seconds."""
    if not isinstance(account, str) or not ACCOUNT.match(account):
        raise TicketError('an account is 1 to 64 letters, digits or _ . @ + -')
    key = secret.encode('utf-8') if isinstance(secret, str) else secret
    body = _b64(json.dumps({'a': account, 'n': shown(name, account), 'e': int((now or time.time()) + seconds),
                            'r': _b64(os.urandom(9))},          # two tickets of a second are two: each comes in once
                           separators=(',', ':')).encode('utf-8'))
    return body + '.' + _b64(hmac.new(key, body.encode('ascii'), hashlib.sha256).digest())


def verify(ticket: object, secret: bytes, now: Optional[float] = None) -> Ticket:
    """What a good ticket says (its account, its name, when it ends); TicketError, with why, of any other."""
    if not isinstance(ticket, str) or ticket.count('.') != 1 or len(ticket) > 1024:
        raise TicketError('That is not a ticket.')
    body, signature = ticket.split('.')
    wanted = hmac.new(secret, body.encode('ascii'), hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(_unb64(signature), wanted):
            raise TicketError('The ticket is not the site\'s.')
        data = json.loads(_unb64(body))
    except (ValueError, TypeError):
        raise TicketError('That is not a ticket.') from None
    if (not isinstance(data, dict) or not isinstance(data.get('a'), str) or not ACCOUNT.match(data['a'])
            or not isinstance(data.get('e'), int)):
        raise TicketError('That is not a ticket.')
    if data['e'] < (now or time.time()):
        raise TicketError('The ticket has expired: sign in again.')
    return Ticket(data['a'], shown(data.get('n'), data['a']), data['e'])
