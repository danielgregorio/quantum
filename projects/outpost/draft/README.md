# Outpost, as it should read

Phase 0 of [PLAN_GAME_SERVER.md](../../../PLAN_GAME_SERVER.md): a small world for five hundred players, written
before any of its tags exist, so that the tags come from a game and not the other way round.

- `outpost.server.q` — the world: a `q:application type="gameserver"` holding one `q:gameserver`.
- `outpost.q` — the game the players run: `qg:connect`, `qg:mirror`, `qg:send`.

Neither runs yet, and nothing builds them: they live in `draft/`, out of the reach of the site's export and of the
games' tests. The plan lists what the parser and the game schema refuse of them, and the phase that brings each
tag. Outpost leaves `draft/` for `projects/outpost/` in Phase 4, when it is playable from start to end, with its
map and its art.
