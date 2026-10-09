# Chess — the rules in the language, and a board for two over the network

`chess.q` is chess: the rules of [Prashanna135/chess](https://github.com/Prashanna135/chess)
(MIT, Godot 4) — legal moves, castling, en passant, promotion, check,
checkmate, stalemate — written in the game language's own statements and
expressions over an array of 64 squares, with the pieces on the screen
mirroring it. White is player 1 and black player 2: on one machine both
click the same board; over the network each machine is one colour, in
lockstep, which for a game by turns is simply "your click arrives". The
piece images are the ones that repository ships, credited to Kenney
(`assets/LICENSE.md`).

Run it: `quantum run projects/chess/chess.q`, then open `projects/chess/godot`
in Godot. Click (or Enter on the arrows' cursor) a piece, then a square.

```
godot --path projects/chess/godot -- --q-host=7777          # white
godot --path projects/chess/godot -- --q-join=HOST:7777     # black
```

## The original, piece by piece

| In the repository | Lines | In `chess.q` |
|---|---|---|
| `board.gd`: `board_state` (64 dictionaries), `setup_pieces` | 60 | `board`, an array of 64 codes (`wK`, `bP`, `""`), and 32 `qg:instance`s |
| `get_pseudo_moves`, `get_pawn_moves`, `get_knight_moves`, `get_king_moves`, `get_sliding_moves` | 85 | `q:function name="pseudo"`: the same rules, in `q:loop` and `q:if` |
| `is_square_attacked`, `find_king`, `is_king_in_check` | 30 | `attacked`, `in_check` |
| `get_legal_moves` (simulate, check), `get_castle_moves` | 30 | `legal_moves`: copy the board (`board[:]`), `apply`, `in_check`, restore |
| `_perform_move`, `move_piece`, promotion, en passant, castling's rook | 60 | `apply` on the array; `qg:put`, `qg:destroy` and `qg:swap` on the pieces |
| `has_any_legal_move`, `check_game_end` | 45 | `any_legal`, the status line |
| `_handle_click`, `select_square`, highlights | 60 | `qg:on-select` with `cursor.row`/`cursor.col`; a `Marker` instance put on the picked square |
| `NetworkManager.gd`: host, join, invite code, send a move | 299 | `<qg:multiplayer players="2" />` |
| `chess_bot.gd` (negamax, tables), clocks, undo/redo, profiles, menus, captured-piece strips | 1,900 | not transcribed |

Not in this version: the fifty-move rule and threefold repetition (the
original has neither), a choice of promotion piece (always a queen), the
bot.

## What the language had to grow

1. **Local variables.** A `q:set` of a name no `q:set` of the scene
   declared, inside a `q:function` or a handler, is the call's own
   variable. Without it, `pseudo` called from `attacked` called from
   `legal_moves` clobbered the list `legal_moves` was building — the
   first real recursion the language met.
2. **An element of an array:** `<q:set name="board" index="{i}" value="wQ" />`.
3. **`qg:put target= x= y=`** to move a thing; `qg:destroy`, `qg:swap` and
   `qg:put` take any name holding a thing (a `thing_at()` result), and a
   named `qg:instance` is a name in its scene (`target="mark"`).
4. `qg:hud position="bottom-center"`.

## The test

`tests/godot/test_godot_chess.py` replays the scholar's mate click by click
from both players (checkmate at move 4), an illegal click that does
nothing, en passant, castling and a promotion, and the same game on two
peers in lockstep.
