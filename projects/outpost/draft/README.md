# Outpost, as it should read

Phase 0 of [PLAN_GAME_SERVER.md](../../../PLAN_GAME_SERVER.md): a small world for five hundred players, written
before any of its tags existed, so that the tags came from a game and not the other way round.

- `outpost.server.q` — the world: a `q:application type="gameserver"` holding one `q:gameserver`.
- `outpost.q` — the game the players run: `qg:connect`, `qg:mirror`, `qg:send`.

Outpost is playable since Phase 4, and Marta and Rhea talk and remember since Phase 5: [`projects/outpost`](..).
This draft stays as what it will read once the later phases bring their tags: the Director, the history and the
admin's page (Phase 6), the party's room and the bots (Phase 7). Nothing builds it: it lives in `draft/`, out of
the reach of the site's export and of the games' tests.
