"""A world's ledger (PLAN_GAME_SERVER.md, Phase 4): its money and its things, made, moved and spent only by q:give,
q:pay, q:take and q:loot, and counted as they are, by asset and by where it happened (the command, the rule, the loot
of a kind). What the holders have of an asset is, at every tick, what was made of it less what was spent:
`balanced()` says so, and an hour of bots holds it.

A holder's assets are fields of it: `bag`, a record of item counts, and a private field a currency (gold). The views
send them to their player as any private field, and a q:set of them is refused: the ledger alone writes them. Its
books are journaled like any write, so a command refused makes, moves and spends nothing.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from quantum.runtime.gameserver.errors import Refused, RuleError
from quantum.runtime.gameserver.life import MISSING


class Ledger:
    """Mixed into World, beside Life."""

    def ledger_fields(self) -> set:
        return ({'bag'} | set(self.definition.currencies)) if self.definition.ledger else set()

    def asset_of(self, item: Any, count: Any, amount: Any, currency: Optional[str],
                 line: Optional[int]) -> Tuple[str, int, bool]:
        """(the asset, how many, is it a currency) of a give, a take or a pay."""
        if (item is None) == (amount is None):
            raise RuleError('an item= or an amount=, one of them', line)
        if item is not None:
            if not isinstance(item, str) or not item:
                raise RuleError(f'item= is the name of an item, not {item!r}', line)
            if self.definition.items and item not in self.definition.items:
                raise RuleError(f'there is no item {item!r} (the world has {", ".join(sorted(self.definition.items))})',
                                line)
            n = count
        else:
            if not self.definition.currencies:
                raise RuleError('amount= is of a currency, and the world has no q:currency', line)
            currency = currency or next(iter(self.definition.currencies))
            if currency not in self.definition.currencies:
                raise RuleError(f'there is no currency {currency!r}', line)
            item, n = currency, amount
        if isinstance(n, float) and n.is_integer():
            n = int(n)
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            raise RuleError(f'{n!r} is not a whole number of {item} (0 or more)', line)
        return item, n, item in self.definition.currencies

    def held(self, holder: dict, asset: str, money: bool) -> int:
        if money:
            value = holder.get(asset)
            return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0
        bag = holder.get('bag')
        return int(bag.get(asset, 0)) if isinstance(bag, dict) else 0

    def _move(self, holder: dict, asset: str, n: int, money: bool, line: Optional[int]) -> None:
        """n more (or fewer) of an asset to a holder's field."""
        if money:
            if not isinstance(holder.get(asset), (int, float)) or isinstance(holder.get(asset), bool):
                raise RuleError(f'{holder.get("id")} holds no {asset} (a field of it that is a number)', line)
            self.write(holder, asset, self.held(holder, asset, True) + n, None, line)
            return
        bag = holder.get('bag')
        if not isinstance(bag, dict):
            raise RuleError(f'{holder.get("id")} has no bag to hold {asset} (a field that is a record)', line)
        left = self.held(holder, asset, False) + n
        if left:
            self.write(bag, asset, left, holder, line)
        else:
            self.put(bag, asset, MISSING)          # none left: out of the bag
            self.dirty.add(holder['id'])

    def book(self, kind: str, asset: str, n: int) -> None:
        """n of an asset made (kind 'made') or spent ('spent') here, in the world's books."""
        if not n:
            return
        books = self.books[kind]
        if asset not in books:
            self.put(books, asset, {})
        self.put(books[asset], self.source, books[asset].get(self.source, 0) + n)

    def give(self, to: dict, item: Any, count: Any, amount: Any, currency: Optional[str], line: Optional[int]) -> None:
        asset, n, money = self.asset_of(item, count, amount, currency, line)
        self._move(to, asset, n, money, line)
        self.book('made', asset, n)

    def take(self, holder: dict, item: Any, count: Any, amount: Any, currency: Optional[str],
             line: Optional[int]) -> None:
        asset, n, money = self.asset_of(item, count, amount, currency, line)
        if self.held(holder, asset, money) < n:
            raise Refused(f'Not enough {asset}.')
        self._move(holder, asset, -n, money, line)
        self.book('spent', asset, n)

    def pay(self, payer: dict, to: dict, amount: Any, currency: Optional[str], line: Optional[int]) -> None:
        asset, n, money = self.asset_of(None, None, amount, currency, line)
        if self.held(payer, asset, money) < n:
            raise Refused(f'Not enough {asset}.')
        self._move(payer, asset, -n, money, line)
        self._move(to, asset, n, money, line)

    def mint_start(self, holder: dict) -> None:
        """What a holder is made with, booked as made at its start."""
        before, self.source = self.source, 'start'
        try:
            for asset, n in self.holdings(holder).items():
                self.book('made', asset, n)
        finally:
            self.source = before

    def spend_all(self, holder: dict, where: str) -> None:
        """A holder gone from the world for good: what it held, booked as spent there."""
        before, self.source = self.source, where
        try:
            for asset, n in self.holdings(holder).items():
                self.book('spent', asset, n)
        finally:
            self.source = before

    def holdings(self, holder: dict) -> Dict[str, int]:
        if not self.definition.ledger:
            return {}
        out = {c: self.held(holder, c, True) for c in self.definition.currencies if c in holder}
        bag = holder.get('bag')
        if isinstance(bag, dict):
            for item, n in bag.items():
                out[item] = out.get(item, 0) + int(n)
        return {k: v for k, v in out.items() if v}

    def balanced(self) -> Dict[str, Tuple[int, int]]:
        """The assets whose holders' sum is not what was made less what was spent: {asset: (held, booked)}."""
        held: Dict[str, int] = {}
        for holder in list(self.entities.values()) + list(self.stored.values()):
            for asset, n in self.holdings(holder).items():
                held[asset] = held.get(asset, 0) + n
        out = {}
        for asset in set(held) | set(self.books['made']) | set(self.books['spent']):
            booked = sum(self.books['made'].get(asset, {}).values()) - sum(self.books['spent'].get(asset, {}).values())
            if held.get(asset, 0) != booked:
                out[asset] = (held.get(asset, 0), booked)
        return out

    # -- what the expressions read of it ---------------------------------------------------------------------------

    def balance(self, x: Any, currency: Any = None) -> int:
        holder = self._entity(x)
        if holder is None or not self.definition.currencies:
            return 0
        currency = currency or next(iter(self.definition.currencies))
        return self.held(holder, currency, True)

    def has(self, x: Any, item: Any, n: Any = 1) -> bool:
        holder = self._entity(x)
        return holder is not None and isinstance(item, str) and self.held(holder, item, False) >= int(n)

    def item_of(self, name: Any) -> Optional[dict]:
        return dict(self.definition.items[name]) if isinstance(name, str) and name in self.definition.items else None

    def item_value(self, name: Any, key: str, default: Any) -> Any:
        props = self.definition.items.get(name) if isinstance(name, str) else None
        return props.get(key, default) if props else default

