# Outpost

A small world for many players at once (PLAN_GAME_SERVER.md, Phase 4): a frontier town, the sewers under it, the
forest east of its gate and a cave north-east, where the Old Bear sleeps. Captain Rhea at the gate gives three
quests: ten rats, five wolves' furs, and the Old Bear's claw, for a party. Old Marta sells and buys.

- `outpost.server.q` — the world: a `q:application type="gameserver"`. Its players are a site's accounts
  (`accounts="site"`): they come in with a ticket the site signs.
- `outpost.q` — the game the players run: it signs in (`qg:sign-in`), draws what the world says each player sees
  (`qg:mirror`) and sends what the player asks (`qg:send`).
- `maps/mainland.tmx` and `assets/` — drawn by `python scripts/art/outpost.py` (CC0).
- `draft/` — Outpost as it will read once Phases 5 to 7 bring their tags: Marta and Rhea who talk (`q:npc`), the
  Director, the history, the admin's page.

To run it on this machine:

    export QUANTUM_WORLD_SECRET=...             # 16 characters or more; the site has the same, in its environment
    quantum gameserver run projects/outpost/outpost.server.q
    quantum run projects/outpost/outpost.q      # the game; its site= says where it signs in

The site signs in a player and answers `{"ticket": "..."}`: any server that knows the accounts and signs with
`quantum.runtime.gameserver.tickets.issue(account, name, secret)` (tests/godot/test_godot_outpost.py has one in
fifteen lines). `quantum gameserver ticket --account ana@site --name Ana` signs one by hand, for a test.

`tests/gameserver/test_outpost.py` plays it from start to end: one hero through the sewers and the pelts, and a
party of four that brings down the Old Bear.
