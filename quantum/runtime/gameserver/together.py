"""Players together (PLAN_GAME_SERVER.md, Phase 4): the chat, a party, a trade between two, and the quests.

The chat, the party and the trade bring their own commands (CommandDef.builtin): run as any command is, as the
player who sent it, at its limit, whole or not at all. A trade moves both sides on the ledger at once, once: when both
players accept the same offers, in whichever order and in whichever tick, the second acceptance moves everything and
ends the trade, so a third finds nothing to accept. What each command changes of parties and trades is journaled,
like any write.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from quantum.runtime.gameserver.errors import Refused, RuleError
from quantum.runtime.gameserver.life import MISSING

MAX_LINE = 200
_CONTROL = re.compile(r'[\x00-\x1f\x7f]')


class Together:
    """Mixed into World, beside Life and Ledger."""

    # -- who is who ----------------------------------------------------------------------------------------------

    def hero_of(self, who: Any) -> Optional[dict]:
        """A player's entity, by its id, its account, the name it shows (when no other shows it), or itself."""
        if isinstance(who, dict):
            return who if self.is_entity(who) and who.get('_player') else None
        if isinstance(who, str):
            if who in self.players:
                return self.entities[self.players[who]]
            entity = self.entities.get(who)
            if entity is not None and entity.get('_player'):
                return entity
            named = [self.entities[e] for e in self.players.values() if self.entities[e].get('name') == who]
            if len(named) == 1:                     # a site's account is ana@site; its hero shows Ana
                return named[0]
        return None

    def tell(self, name: str, value: Any, accounts: List[str]) -> None:
        """An event to these players alone."""
        from quantum.runtime.gameserver.world import Event, plain
        self.events.append(Event({'name': name, 'value': plain(value)}, None, None, False, sorted(set(accounts))))

    def builtin(self, name: str, me: dict, args: Dict[str, Any]) -> None:
        if name == 'chat':
            self.chat(me, args['channel'], args['text'])
        elif name == 'whisper':
            self.whisper(me, args['to'], args['text'])
        elif name == 'party-invite':
            self.party_invite(me, args['who'])
        elif name == 'party-accept':
            self.party_accept(me, args['who'])
        elif name == 'party-leave':
            self.party_leave(me)
        elif name == 'trade-offer':
            self.trade_offer(me, args['who'], args['gold'], args['items'])
        elif name == 'trade-accept':
            self.trade_accept(me, args['who'])
        elif name == 'trade-cancel':
            self.trade_cancel(me, args['who'])
        else:
            raise RuleError(f'no command {name!r} of the world\'s own')

    # -- the chat ----------------------------------------------------------------------------------------------

    def clean(self, text: Any) -> str:
        if not isinstance(text, str) or not text.strip():
            raise Refused('Say something.')
        text = _CONTROL.sub('', text).strip()[:MAX_LINE]
        for word in self.definition.chat.words if self.definition.chat else ():
            text = re.sub(rf'(?i)\b{re.escape(word)}\b', '*' * len(word), text)
        return text

    def chat(self, me: dict, channel: Any, text: Any) -> None:
        channels = self.definition.chat.channels
        if not isinstance(channel, str) or channel not in channels:
            raise Refused(f'There is no channel {channel!r} ({", ".join(channels)}).')
        line = {'channel': channel, 'from': me.get('name', me['id']), 'text': self.clean(text)}
        if channel == 'party':
            party = self.parties.get(me.get('party') or '')
            if party is None:
                raise Refused('You are in no party.')
            to = [self.entities[m]['_player'] for m in party['members'] if m in self.entities]
        elif channels[channel] is None:
            to = list(self.players)
        else:
            here, reach = self.tile_of(me), channels[channel]
            to = []
            if here is not None:
                for eid in self.near_ids(here, reach):
                    other = self.entities[eid]
                    there = self.tile_of(other)
                    if other.get('_player') and there and max(abs(there[0] - here[0]),
                                                              abs(there[1] - here[1])) <= reach:
                        to.append(other['_player'])
        self.tell('chat', line, to)

    def whisper(self, me: dict, who: Any, text: Any) -> None:
        other = self.hero_of(who)
        if other is None:
            raise Refused('Nobody of that name here.')
        line = {'channel': 'whisper', 'from': me.get('name', me['id']), 'to': other.get('name', other['id']),
                'text': self.clean(text)}
        self.tell('chat', line, [me['_player'], other['_player']])

    def say(self, channel: str, to: Any, text: str, line: Optional[int]) -> None:
        """q:say: a line of the world's own, to a player or all."""
        if to == 'all' or to is None:
            accounts = list(self.players)
        else:
            hero = self.hero_of(to)
            if hero is None:
                raise RuleError('q:say to= is a player\'s entity, or all', line)
            accounts = [hero['_player']]
        self.tell('chat', {'channel': channel, 'from': 'world', 'text': str(text)[:MAX_LINE]}, accounts)

    # -- parties -----------------------------------------------------------------------------------------------

    def party_invite(self, me: dict, who: Any) -> None:
        other = self.hero_of(who)
        if other is None or other is me:
            raise Refused('Nobody of that name here.')
        if other.get('party'):
            raise Refused(f'{other.get("name", other["id"])} is in a party.')
        pid = me.get('party')
        if not pid:
            self.counters['party'] = self.counters.get('party', 0) + 1
            pid = f'party-{self.counters["party"]}'
            self.put(self.parties, pid, {'members': [me['id']], 'invited': []})
            self.write(me, 'party', pid, None, None)
        party = self.parties[pid]
        if len(party['members']) >= self.definition.party_size:
            raise Refused('The party is full.')
        if other['id'] not in party['invited']:
            self.put(self.parties, pid, {**party, 'invited': party['invited'] + [other['id']]})
        self.tell('party', {'invited': other['id'], 'by': me['id'], 'party': pid},
                  [me['_player'], other['_player']])

    def party_accept(self, me: dict, who: Any) -> None:
        other = self.hero_of(who)
        party = self.parties.get(other.get('party') or '') if other else None
        if party is None or me['id'] not in party['invited']:
            raise Refused('No one invited you.')
        if me.get('party'):
            raise Refused('You are in a party already.')
        if len(party['members']) >= self.definition.party_size:
            raise Refused('The party is full.')
        pid = other['party']
        self.put(self.parties, pid, {'members': party['members'] + [me['id']],
                                     'invited': [i for i in party['invited'] if i != me['id']]})
        self.write(me, 'party', pid, None, None)
        self._tell_party(pid, {'joined': me['id'], 'party': pid})

    def party_leave(self, me: dict) -> None:
        pid = me.get('party') or ''
        party = self.parties.get(pid)
        if party is None:
            raise Refused('You are in no party.')
        members = [m for m in party['members'] if m != me['id']]
        self.write(me, 'party', '', None, None)
        self._tell_party(pid, {'left': me['id'], 'party': pid}, extra=[me['_player']])
        if len(members) <= 1:                                # one alone is no party
            for m in members:
                if m in self.entities:
                    self.write(self.entities[m], 'party', '', None, None)
            self.put(self.parties, pid, MISSING)
        else:
            self.put(self.parties, pid, {**party, 'members': members})

    def _tell_party(self, pid: str, value: dict, extra: List[str] = ()) -> None:
        party = self.parties.get(pid) or {'members': []}
        to = [self.entities[m]['_player'] for m in party['members'] if m in self.entities] + list(extra)
        self.tell('party', value, to)

    def party_of(self, x: Any) -> List[dict]:
        entity = self._entity(x)
        if entity is None:
            return []
        party = self.parties.get(entity.get('party') or '')
        if party is None:
            return [entity]
        return [self.entities[m] for m in party['members'] if m in self.entities]

    def party_near(self, x: Any, n: Any = 10) -> List[dict]:
        """The party of x within n tiles of it (x alone, with no party)."""
        entity = self._entity(x)
        here = self.tile_of(entity) if entity else None
        if here is None:
            return [entity] if entity else []
        out = []
        for member in self.party_of(entity):
            there = self.tile_of(member)
            if there is not None and max(abs(there[0] - here[0]), abs(there[1] - here[1])) <= int(n):
                out.append(member)
        return out

    # -- trades ------------------------------------------------------------------------------------------------

    def _trade_key(self, a: dict, b: dict) -> str:
        return '|'.join(sorted((a['id'], b['id'])))

    def trade_offer(self, me: dict, who: Any, gold: Any, items: Any) -> None:
        other = self.hero_of(who)
        if other is None or other is me:
            raise Refused('Nobody of that name here.')
        currency = next(iter(self.definition.currencies), None)
        gold = int(gold) if isinstance(gold, (int, float)) and not isinstance(gold, bool) and gold == int(gold) else -1
        if gold < 0 or (gold and currency is None):
            raise Refused('gold is a whole number, 0 or more.')
        if not isinstance(items, dict) or not all(isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool)
                                                  and v > 0 for k, v in items.items()):
            raise Refused('items is a record of counts: {"cheese": 2}.')
        if currency and self.held(me, currency, True) < gold:
            raise Refused(f'Not enough {currency}.')
        for item, n in items.items():
            if self.held(me, item, False) < n:
                raise Refused(f'Not enough {item}.')
        key = self._trade_key(me, other)
        trade = self.trades.get(key) or {'between': sorted((me['id'], other['id'])), 'offers': {}, 'accepted': []}
        offers = {**trade['offers'], me['id']: {'gold': gold, 'items': dict(sorted(items.items()))}}
        self.put(self.trades, key, {**trade, 'offers': offers, 'accepted': []})   # what was accepted is no more
        self._tell_trade(key)

    def trade_accept(self, me: dict, who: Any) -> None:
        other = self.hero_of(who)
        key = self._trade_key(me, other) if other else ''
        trade = self.trades.get(key)
        if trade is None:
            raise Refused('No trade with them.')
        accepted = sorted(set(trade['accepted']) | {me['id']})
        if len(accepted) < 2:
            self.put(self.trades, key, {**trade, 'accepted': accepted})
            self._tell_trade(key)
            return
        currency = next(iter(self.definition.currencies), None)
        for giver, taker in ((me, other), (other, me)):          # both sides, at once: all or nothing
            offer = trade['offers'].get(giver['id'], {'gold': 0, 'items': {}})
            if offer['gold']:
                self.pay(giver, taker, offer['gold'], currency, None)
            for item, n in offer['items'].items():
                if self.held(giver, item, False) < n:
                    raise Refused(f'{giver.get("name", giver["id"])} has not enough {item} now.')
                self._move(giver, item, -n, False, None)
                self._move(taker, item, n, False, None)
        self.put(self.trades, key, MISSING)
        self.tell('trade', {'between': trade['between'], 'done': True, 'offers': trade['offers']},
                  [me['_player'], other['_player']])

    def trade_cancel(self, me: dict, who: Any) -> None:
        other = self.hero_of(who)
        key = self._trade_key(me, other) if other else ''
        trade = self.trades.get(key)
        if trade is None:
            raise Refused('No trade with them.')
        self.put(self.trades, key, MISSING)
        self.tell('trade', {'between': trade['between'], 'cancelled': True},
                  [self.entities[e]['_player'] for e in trade['between'] if e in self.entities])

    def _tell_trade(self, key: str) -> None:
        trade = self.trades[key]
        self.tell('trade', {'between': trade['between'], 'offers': trade['offers'], 'accepted': trade['accepted']},
                  [self.entities[e]['_player'] for e in trade['between'] if e in self.entities])

    def part(self, hero: dict) -> None:
        """A hero leaving the world: out of its party, its trades cancelled."""
        if hero.get('party') and hero['party'] in self.parties:
            self.party_leave(hero)
        for key in sorted(k for k, t in self.trades.items() if hero['id'] in t['between']):
            trade = self.trades[key]
            self.put(self.trades, key, MISSING)
            self.tell('trade', {'between': trade['between'], 'cancelled': True},
                      [self.entities[e]['_player'] for e in trade['between']
                       if e in self.entities and e != hero['id']])

    # -- quests ------------------------------------------------------------------------------------------------

    def quest_of(self, x: Any) -> Optional[Any]:
        entity = self._entity(x)
        quest = entity.get('quest') if entity else None
        name = quest.get('name') if isinstance(quest, dict) else None
        return self.definition.quests.get(name) if isinstance(name, str) else None

    def quest_goal(self, x: Any) -> str:
        quest = self.quest_of(x)
        return f'{quest.goal[0]}:{quest.goal[1]}' if quest else ''

    def quest_done(self, x: Any) -> bool:
        quest = self.quest_of(x)
        if quest is None:
            return False
        kind, what, n = quest.goal
        if kind == 'bring':
            return self.has(x, what, n)
        done = self._entity(x)['quest'].get('done', 0)
        return isinstance(done, (int, float)) and done >= n

    def reward(self, to: dict, name: Any, line: Optional[int]) -> None:
        quest = self.definition.quests.get(name) if isinstance(name, str) else None
        if quest is None:
            raise RuleError(f'q:reward quest=: there is no quest {name!r}', line)
        for key, n in quest.reward:
            if key in self.definition.currencies:
                self.give(to, None, None, n, key, line)
            elif key.startswith('item:'):
                self.give(to, key[5:], n, None, None, line)
            else:
                if not isinstance(to.get(key), (int, float)) or isinstance(to.get(key), bool):
                    raise RuleError(f'q:reward {key}:{n}: {to.get("id")} has no field {key} that is a number', line)
                self.write(to, key, to[key] + n, None, line)
