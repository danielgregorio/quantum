<q:application id="chess" type="game">

  <!-- Chess: the rules of github.com/Prashanna135/chess (MIT) — legal moves,
       castling, en passant, promotion, check, checkmate and stalemate —
       written in the game language's own statements and expressions over an
       array of 64 squares; the pieces on the screen mirror it. White is
       player 1, black player 2: on one machine both click the same board;
       over the network each machine is one colour, in lockstep. README.md
       maps the original to this file. -->

  <qg:tileset name="board" src="assets/board.png" tile="62" />
  <qg:spritesheet name="pieces" src="assets/pieces.png" tile="60" />
  <qg:multiplayer players="2" delay="2" start="game" />

  <qg:prefab name="wK" tag="piece" sheet="pieces" frame="0" hitbox="60x60" />
  <qg:prefab name="wQ" tag="piece" sheet="pieces" frame="1" hitbox="60x60" />
  <qg:prefab name="wR" tag="piece" sheet="pieces" frame="2" hitbox="60x60" />
  <qg:prefab name="wB" tag="piece" sheet="pieces" frame="3" hitbox="60x60" />
  <qg:prefab name="wN" tag="piece" sheet="pieces" frame="4" hitbox="60x60" />
  <qg:prefab name="wP" tag="piece" sheet="pieces" frame="5" hitbox="60x60" />
  <qg:prefab name="bK" tag="piece" sheet="pieces" frame="6" hitbox="60x60" />
  <qg:prefab name="bQ" tag="piece" sheet="pieces" frame="7" hitbox="60x60" />
  <qg:prefab name="bR" tag="piece" sheet="pieces" frame="8" hitbox="60x60" />
  <qg:prefab name="bB" tag="piece" sheet="pieces" frame="9" hitbox="60x60" />
  <qg:prefab name="bN" tag="piece" sheet="pieces" frame="10" hitbox="60x60" />
  <qg:prefab name="bP" tag="piece" sheet="pieces" frame="11" hitbox="60x60" />
  <qg:prefab name="Marker" tag="marker" sheet="board" frame="1" hitbox="4x4" gd:modulate="#e0d040a0" gd:z_index="-1" />

  <!-- The title: both colours on one board, or white and black on two machines. -->
  <qg:scene name="title" width="496" height="540" background="#2a2520">
    <qg:hud position="top-center" size="40"><qg:text value="{'CHESS'}" /></qg:hud>
    <qg:lobby local="game" local-label="Two players, one board" size="18" />
  </qg:scene>

  <qg:scene name="game" width="496" height="540" background="#2a2520">
    <!-- row 0 is the eighth rank (black's home), row 7 the first; a square is board[row * 8 + col] -->
    <q:set name="board" type="array" value="{['bR','bN','bB','bQ','bK','bB','bN','bR', 'bP','bP','bP','bP','bP','bP','bP','bP', '','','','','','','','', '','','','','','','','', '','','','','','','','', '','','','','','','','', 'wP','wP','wP','wP','wP','wP','wP','wP', 'wR','wN','wB','wQ','wK','wB','wN','wR']}" />
    <q:set name="turn" value="w" />
    <q:set name="sel_r" value="-1" type="number" />
    <q:set name="sel_c" value="-1" type="number" />
    <q:set name="legal" type="array" value="{[]}" />
    <q:set name="ep_col" value="-1" type="number" />
    <q:set name="moved" type="array" value="{[]}" />
    <q:set name="status" value="White to move" />
    <q:set name="finished" value="false" type="boolean" />

    <qg:tilemap tileset="board">
1,2,1,2,1,2,1,2
2,1,2,1,2,1,2,1
1,2,1,2,1,2,1,2
2,1,2,1,2,1,2,1
1,2,1,2,1,2,1,2
2,1,2,1,2,1,2,1
1,2,1,2,1,2,1,2
2,1,2,1,2,1,2,1
    </qg:tilemap>
    <qg:cursor player="1" grid="62" />
    <qg:cursor player="2" grid="62" />
    <!-- the picked square's mark, kept off the board until a piece is picked -->
    <qg:instance prefab="Marker" name="mark" x="-100" y="-100" />

    <qg:instance prefab="bR" x="31" y="31" /><qg:instance prefab="bN" x="93" y="31" /><qg:instance prefab="bB" x="155" y="31" /><qg:instance prefab="bQ" x="217" y="31" />
    <qg:instance prefab="bK" x="279" y="31" /><qg:instance prefab="bB" x="341" y="31" /><qg:instance prefab="bN" x="403" y="31" /><qg:instance prefab="bR" x="465" y="31" />
    <qg:instance prefab="bP" x="31" y="93" /><qg:instance prefab="bP" x="93" y="93" /><qg:instance prefab="bP" x="155" y="93" /><qg:instance prefab="bP" x="217" y="93" />
    <qg:instance prefab="bP" x="279" y="93" /><qg:instance prefab="bP" x="341" y="93" /><qg:instance prefab="bP" x="403" y="93" /><qg:instance prefab="bP" x="465" y="93" />
    <qg:instance prefab="wP" x="31" y="403" /><qg:instance prefab="wP" x="93" y="403" /><qg:instance prefab="wP" x="155" y="403" /><qg:instance prefab="wP" x="217" y="403" />
    <qg:instance prefab="wP" x="279" y="403" /><qg:instance prefab="wP" x="341" y="403" /><qg:instance prefab="wP" x="403" y="403" /><qg:instance prefab="wP" x="465" y="403" />
    <qg:instance prefab="wR" x="31" y="465" /><qg:instance prefab="wN" x="93" y="465" /><qg:instance prefab="wB" x="155" y="465" /><qg:instance prefab="wQ" x="217" y="465" />
    <qg:instance prefab="wK" x="279" y="465" /><qg:instance prefab="wB" x="341" y="465" /><qg:instance prefab="wN" x="403" y="465" /><qg:instance prefab="wR" x="465" y="465" />

    <qg:hud position="bottom-center" size="14"><qg:text bind="status" /></qg:hud>

    <!-- what is on a square ("x" off the board), whose it is -->
    <q:function name="at" params="r, c">
      <q:if condition="{r &lt; 0 or r &gt; 7 or c &lt; 0 or c &gt; 7}"><q:return value="{'x'}" /></q:if>
      <q:return value="{board[r * 8 + c]}" />
    </q:function>
    <q:function name="own" params="p, color">
      <q:return value="{p != '' and p != 'x' and p[0:1] == color}" />
    </q:function>
    <q:function name="enemy" params="p, color">
      <q:return value="{p != '' and p != 'x' and p[0:1] != color}" />
    </q:function>
    <q:function name="other_color" params="color">
      <q:return value="{'b' if color == 'w' else 'w'}" />
    </q:function>

    <!-- where a piece may go by its own rule (attacks only, for a pawn, when atk) -->
    <q:function name="pseudo" params="r, c, atk">
      <q:set name="result" value="{[]}" />
      <q:set name="p" value="{at(r, c)}" />
      <q:set name="color" value="{p[0:1]}" />
      <q:set name="kind" value="{p[1:2]}" />
      <q:if condition="{kind == 'P'}">
        <q:set name="dir" value="{-1 if color == 'w' else 1}" />
        <q:if condition="{not atk and at(r + dir, c) == ''}">
          <q:set name="result" value="{result + [[r + dir, c]]}" />
          <q:if condition="{(r == 6 and color == 'w' or r == 1 and color == 'b') and at(r + 2 * dir, c) == ''}">
            <q:set name="result" value="{result + [[r + 2 * dir, c]]}" />
          </q:if>
        </q:if>
        <q:loop var="dc" items="{[-1, 1]}">
          <q:if condition="{atk or enemy(at(r + dir, c + dc), color)}">
            <q:if condition="{at(r + dir, c + dc) != 'x'}">
              <q:set name="result" value="{result + [[r + dir, c + dc]]}" />
            </q:if>
          </q:if>
          <q:if condition="{not atk and ep_col == c + dc and r == (3 if color == 'w' else 4)}">
            <q:set name="result" value="{result + [[r + dir, c + dc]]}" />
          </q:if>
        </q:loop>
      </q:if>
      <q:if condition="{kind == 'N' or kind == 'K'}">
        <q:set name="steps" value="{[[1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2]] if kind == 'N' else [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]]}" />
        <q:loop var="s" items="{steps}">
          <q:set name="q" value="{at(r + s[0], c + s[1])}" />
          <q:if condition="{q != 'x' and not own(q, color)}">
            <q:set name="result" value="{result + [[r + s[0], c + s[1]]]}" />
          </q:if>
        </q:loop>
      </q:if>
      <q:if condition="{kind == 'R' or kind == 'B' or kind == 'Q'}">
        <q:set name="dirs" value="{[]}" />
        <q:if condition="{kind != 'B'}"><q:set name="dirs" value="{dirs + [[1, 0], [-1, 0], [0, 1], [0, -1]]}" /></q:if>
        <q:if condition="{kind != 'R'}"><q:set name="dirs" value="{dirs + [[1, 1], [1, -1], [-1, 1], [-1, -1]]}" /></q:if>
        <q:loop var="d" items="{dirs}">
          <q:set name="blocked" value="false" />
          <q:loop var="n" from="1" to="7">
            <q:if condition="{not blocked}">
              <q:set name="q" value="{at(r + d[0] * n, c + d[1] * n)}" />
              <q:if condition="{q == 'x' or own(q, color)}">
                <q:set name="blocked" value="true" />
              <q:else>
                <q:set name="result" value="{result + [[r + d[0] * n, c + d[1] * n]]}" />
                <q:if condition="{q != ''}"><q:set name="blocked" value="true" /></q:if>
              </q:else>
              </q:if>
            </q:if>
          </q:loop>
        </q:loop>
      </q:if>
      <q:return value="{result}" />
    </q:function>

    <q:function name="attacked" params="r, c, by">
      <q:loop var="i" from="0" to="63">
        <q:if condition="{own(board[i], by)}">
          <q:if condition="{[r, c] in pseudo(i // 8, i % 8, true)}"><q:return value="{true}" /></q:if>
        </q:if>
      </q:loop>
      <q:return value="{false}" />
    </q:function>
    <q:function name="in_check" params="color">
      <q:loop var="i" from="0" to="63">
        <q:if condition="{board[i] == color + 'K'}">
          <q:return value="{attacked(i // 8, i % 8, other_color(color))}" />
        </q:if>
      </q:loop>
      <q:return value="{false}" />
    </q:function>

    <!-- the board after a move: the rook of a castling, the pawn of an en passant, a promotion -->
    <q:function name="apply" params="r1, c1, r2, c2">
      <q:set name="p" value="{board[r1 * 8 + c1]}" />
      <q:if condition="{p[1:2] == 'P' and c1 != c2 and board[r2 * 8 + c2] == ''}">
        <q:set name="board" index="{r1 * 8 + c2}" value="" />
      </q:if>
      <q:if condition="{p[1:2] == 'K' and c2 - c1 == 2}">
        <q:set name="board" index="{r1 * 8 + 5}" value="{board[r1 * 8 + 7]}" />
        <q:set name="board" index="{r1 * 8 + 7}" value="" />
      </q:if>
      <q:if condition="{p[1:2] == 'K' and c1 - c2 == 2}">
        <q:set name="board" index="{r1 * 8 + 3}" value="{board[r1 * 8]}" />
        <q:set name="board" index="{r1 * 8}" value="" />
      </q:if>
      <q:set name="board" index="{r1 * 8 + c1}" value="" />
      <q:set name="board" index="{r2 * 8 + c2}" value="{p[0:1] + 'Q' if p[1:2] == 'P' and (r2 == 0 or r2 == 7) else p}" />
    </q:function>

    <!-- the moves that leave the king safe, castling included -->
    <q:function name="legal_moves" params="r, c">
      <q:set name="p" value="{at(r, c)}" />
      <q:set name="color" value="{p[0:1]}" />
      <q:set name="candidates" value="{pseudo(r, c, false)}" />
      <q:if condition="{p[1:2] == 'K' and not (color + 'K') in moved and not in_check(color)}">
        <q:if condition="{not (color + 'Rh') in moved and at(r, 5) == '' and at(r, 6) == '' and at(r, 7) == color + 'R' and not attacked(r, 5, other_color(color)) and not attacked(r, 6, other_color(color))}">
          <q:set name="candidates" value="{candidates + [[r, 6]]}" />
        </q:if>
        <q:if condition="{not (color + 'Ra') in moved and at(r, 1) == '' and at(r, 2) == '' and at(r, 3) == '' and at(r, 0) == color + 'R' and not attacked(r, 3, other_color(color)) and not attacked(r, 2, other_color(color))}">
          <q:set name="candidates" value="{candidates + [[r, 2]]}" />
        </q:if>
      </q:if>
      <q:set name="result" value="{[]}" />
      <q:loop var="m" items="{candidates}">
        <q:set name="saved" value="{board[:]}" />
        <q:call function="apply" args="r, c, m[0], m[1]" />
        <q:set name="ok" value="{not in_check(color)}" />
        <q:set name="board" value="{saved}" />
        <q:if condition="{ok}"><q:set name="result" value="{result + [m]}" /></q:if>
      </q:loop>
      <q:return value="{result}" />
    </q:function>
    <q:function name="any_legal" params="color">
      <q:loop var="i" from="0" to="63">
        <q:if condition="{own(board[i], color)}">
          <q:if condition="{len(legal_moves(i // 8, i % 8)) &gt; 0}"><q:return value="{true}" /></q:if>
        </q:if>
      </q:loop>
      <q:return value="{false}" />
    </q:function>

    <q:function name="clear_mark">
      <qg:put target="mark" x="-100" y="-100" />
      <q:set name="sel_r" value="-1" />
      <q:set name="sel_c" value="-1" />
      <q:set name="legal" value="{[]}" />
    </q:function>

    <!-- a click: pick up one of your pieces, or put the picked one on a legal square -->
    <qg:on-select>
      <q:if condition="{not finished and (cursor.player == 1 and turn == 'w' or cursor.player == 2 and turn == 'b')}">
        <q:set name="r" value="{cursor.row}" />
        <q:set name="c" value="{cursor.col}" />
        <q:set name="act" value="{'move' if sel_r &gt;= 0 and [r, c] in legal else ('pick' if own(at(r, c), turn) else 'clear')}" />
        <q:if condition="{act == 'move'}">
          <q:set name="mover" value="{thing_at('piece', sel_c * 62 + 31, sel_r * 62 + 31)}" />
          <q:set name="p" value="{board[sel_r * 8 + sel_c]}" />
          <!-- what the move takes: the piece on the square, or the pawn passed en passant -->
          <q:set name="taken" value="{thing_at('piece', c * 62 + 31, r * 62 + 31)}" />
          <q:if condition="{taken == null and p[1:2] == 'P' and c != sel_c}">
            <q:set name="taken" value="{thing_at('piece', c * 62 + 31, sel_r * 62 + 31)}" />
          </q:if>
          <q:if condition="{taken != null}"><qg:destroy target="taken" /></q:if>
          <q:if condition="{p[1:2] == 'K' and c - sel_c == 2}">
            <q:set name="taken" value="{thing_at('piece', 7 * 62 + 31, r * 62 + 31)}" />
            <qg:put target="taken" x="{5 * 62 + 31}" y="{r * 62 + 31}" />
          </q:if>
          <q:if condition="{p[1:2] == 'K' and sel_c - c == 2}">
            <q:set name="taken" value="{thing_at('piece', 31, r * 62 + 31)}" />
            <qg:put target="taken" x="{3 * 62 + 31}" y="{r * 62 + 31}" />
          </q:if>
          <qg:put target="mover" x="{c * 62 + 31}" y="{r * 62 + 31}" />
          <q:if condition="{p[1:2] == 'P' and (r == 0 or r == 7)}">
            <q:if condition="{turn == 'w'}"><qg:swap target="mover" prefab="wQ" /><q:else><qg:swap target="mover" prefab="bQ" /></q:else></q:if>
          </q:if>
          <q:call function="apply" args="sel_r, sel_c, r, c" />
          <!-- the rights and the en passant square after the move -->
          <q:if condition="{p[1:2] == 'K'}"><q:set name="moved" value="{moved + [turn + 'K']}" /></q:if>
          <q:if condition="{p[1:2] == 'R' and sel_c == 0}"><q:set name="moved" value="{moved + [turn + 'Ra']}" /></q:if>
          <q:if condition="{p[1:2] == 'R' and sel_c == 7}"><q:set name="moved" value="{moved + [turn + 'Rh']}" /></q:if>
          <q:set name="ep_col" value="{c if p[1:2] == 'P' and abs(r - sel_r) == 2 else -1}" />
          <q:set name="turn" value="{other_color(turn)}" />
          <q:call function="clear_mark" />
          <q:set name="status" value="{('White' if turn == 'w' else 'Black') + ' to move'}" />
          <q:if condition="{not any_legal(turn)}">
            <q:set name="finished" value="true" />
            <q:set name="status" value="{('Checkmate - ' + ('Black' if turn == 'w' else 'White') + ' wins') if in_check(turn) else 'Stalemate'}" />
          <q:elseif condition="{in_check(turn)}">
            <q:set name="status" value="{status + ' - check'}" />
          </q:elseif>
          </q:if>
        </q:if>
        <q:if condition="{act == 'pick'}">
          <q:call function="clear_mark" />
          <q:set name="sel_r" value="{r}" />
          <q:set name="sel_c" value="{c}" />
          <q:set name="legal" value="{legal_moves(r, c)}" />
          <qg:put target="mark" x="{cursor.x}" y="{cursor.y}" />
        </q:if>
        <q:if condition="{act == 'clear'}">
          <q:call function="clear_mark" />
        </q:if>
      </q:if>
    </qg:on-select>
  </qg:scene>

</q:application>
