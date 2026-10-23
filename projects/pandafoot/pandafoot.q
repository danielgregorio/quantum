<q:application id="pandafoot" type="game">

  <!-- PandaFoot: a football manager after Elifoot 2 (PLAN_PANDAFOOT.md, Phase 2).
       There is always a next match: you prepare it, play it, see the result,
       and the season goes on. Four divisions of ten clubs, home and away, two
       up and two down, for one manager or two to four taking turns at one
       machine, each starting at a small club of the fourth. The rules are
       pandafoot's GAME_DESIGN.md v0.2: strength (força) 1 to 50, four
       positions, seven traits, a genius hidden in a small club, salaries by the
       month paid by the week, the live round with every match of it in the
       same minute.

       Drawn as a text screen of the DOS days: an 80 by 25 grid of a
       monospaced font (DejaVu Sans Mono, its licence beside it), white on
       blue, boxes drawn by scripts/art/pandafoot.py (CC0). Written in English,
       played in Portuguese and Spanish too (qg:language, at the end). -->

  <!-- ===== The world: what a new game makes, and what a season changes ===== -->
  <q:set name="clubs" value="[]" type="array" />          <!-- the forty clubs, each a record (see new_club); club.div its division -->
  <q:set name="fixtures" value="[]" type="array" />       <!-- 18 rounds, each twenty [home, away]: five of each division -->
  <q:set name="managers" value="[]" type="array" />       <!-- {name, club, patience, career}: one to four, taking turns -->
  <q:set name="jobs" value="[]" type="array" />           <!-- what waits for a manager: {who, kind: sacked or offer, clubs} -->
  <q:set name="retired" value="[]" type="array" />        <!-- the managers whose careers ended: {name, career} -->
  <q:set name="turn" value="0" type="number" />           <!-- whose screens these are -->
  <q:set name="matchday" value="0" type="number" />       <!-- the next round, from 0 -->
  <q:set name="season" value="2026" type="number" />
  <q:set name="world" value="7" type="number" />           <!-- the world's number: the same number, the same world -->
  <q:set name="slot" value="1" type="number" />            <!-- the save this game goes into -->
  <q:set name="news" value="[]" type="array" />           <!-- what the papers say, newest first: {text, arg} -->
  <q:set name="last" value="[]" type="array" />           <!-- the last round's matches, for its results -->
  <q:set name="champion" value="-1" type="number" />
  <q:set name="viewing" value="-1" type="number" />       <!-- the club whose squad is shown, from the table (-1: the manager's) -->

  <!-- the numbers of the design, in one place; the names are names in every language -->
  <q:set name="club_names" value='["Panda FC", "Bambu United", "Urso Polar", "Tigre Branco", "Leão Dourado", "Onça Pintada", "Gavião Real", "Lobo Guará", "Jacaré FC", "Arara Azul", "Coala City", "Pinguim FC", "Capivara EC", "Tucano FC", "Raposa EC", "Coruja AC", "Falcão United", "Boto Rosa", "Cervo FC", "Zebra City", "Tamanduá", "Jaguatirica", "Mico-Leão", "Tatu-Bola", "Quati AC", "Peixe-Boi", "Ouriço FC", "Preguiça EC", "Flamingo FC", "Pelicano EC", "Sabiá United", "Gambá City", "Lhama FC", "Canguru AC", "Lontra AC", "Tartaruga", "Camelo FC", "Esquilo EC", "Marreco AC", "Siri FC"]' type="array" />
  <q:set name="club_short" value='["PAN", "BAM", "URS", "TIG", "LEO", "ONC", "GAV", "LOB", "JAC", "ARA", "COA", "PIN", "CAP", "TUC", "RAP", "COR", "FAL", "BOT", "CER", "ZEB", "TAM", "JAG", "MIC", "TAT", "QUA", "PEI", "OUR", "PRE", "FLA", "PEL", "SAB", "GAM", "LHA", "CAN", "LON", "TAR", "CAM", "ESQ", "MAR", "SIR"]' type="array" />
  <q:set name="first_names" value='["João", "Pedro", "Lucas", "Mateus", "Rafael", "Gabriel", "Bruno", "Diego", "Felipe", "Thiago", "André", "Caio", "Danilo", "Everton", "Fábio", "Gustavo", "Hugo", "Igor", "Júlio", "Léo", "Marcos", "Nando", "Otávio", "Paulo", "Renan", "Sérgio", "Tiago", "Vítor", "Wesley", "Zé", "Alex", "Beto", "Cadu", "Davi", "Edu", "Fred", "Gil", "Heitor", "Ivan", "Jorge", "Kleber", "Luan", "Mário", "Nilton", "Oscar", "Rui", "Saulo", "Téo", "Valter", "Vini"]' type="array" />
  <q:set name="surnames" value='["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Ferreira", "Rodrigues", "Almeida", "Nascimento", "Carvalho", "Gomes", "Martins", "Araújo", "Ribeiro", "Barbosa", "Rocha", "Dias", "Moreira", "Teixeira", "Mendes", "Freitas", "Cardoso", "Ramos", "Pinto", "Moura", "Batista", "Viana", "Correia", "Lopes", "Melo", "Nunes", "Castro", "Campos", "Duarte", "Fonseca", "Guimarães", "Lacerda", "Macedo", "Neves", "Pacheco", "Queiroz", "Reis", "Sales", "Tavares", "Vasconcelos", "Xavier", "Brito", "Siqueira"]' type="array" />
  <q:set name="nicknames" value='["Bambuzinho", "Pandinha", "Tico", "Biro", "Dudu", "Kaká", "Juninho", "Zinho", "Pelezinho", "Romarinho", "Tatu", "Neguebinha", "Canhota", "Foguete", "Muralhão", "Bolinha", "Pirulito", "Ratinho", "Biscoito", "Sabiá", "Grilo", "Pipoca", "Formiga", "Tucano", "Mosquito", "Baiano", "Mineiro", "Tchê", "Galego", "Russo"]' type="array" />
  <q:set name="formations" value='["4-4-2", "4-3-3", "5-3-2", "4-5-1", "3-4-3", "5-4-1"]' type="array" />
  <q:set name="styles" value='["Balanced", "Attacking", "All-out attack", "Defensive", "Park the bus", "Counter-attack", "Kamikaze"]' type="array" />
  <q:set name="objectives" value='["Win", "Draw", "Avoid defeat", "By hand", "Auto"]' type="array" />
  <q:set name="honours" value="[]" type="array" />         <!-- the seasons past, newest first: {season, champions, scorer} -->

  <!-- ===== The look: a text screen ===== -->
  <qg:spritesheet name="frame" src="assets/frame.png" tile="24" slice="8" />   <!-- a double line, grey on blue -->
  <qg:sound name="goal" src="assets/goal.ogg" bus="effects" />
  <qg:sound name="whistle" src="assets/whistle.ogg" bus="effects" />
  <qg:sound name="final" src="assets/final.ogg" bus="effects" />

  <!-- ===== The keys: every screen a hotkey away ===== -->
  <qg:input action="lineup" keys="F1" />
  <qg:input action="tactics" keys="F2" />
  <qg:input action="squad" keys="F3" />
  <qg:input action="finances" keys="F5" />
  <qg:input action="standings" keys="F7" />
  <qg:input action="pause" keys="Space, P" />
  <qg:input action="other" keys="Tab" />
  <qg:input action="faster" keys="Equal, KpAdd" />
  <qg:input action="slower" keys="Minus, KpSubtract" />
  <qg:input action="undo" keys="C" />        <!-- undo an automatic change of tactics -->
  <qg:input action="auto" keys="A" />        <!-- the line-up picked by the computer -->

  <!-- ===== Little helpers ===== -->

  <!-- a new game starts from nothing: no managers, the first season (a game played before leaves nothing behind) -->
  <q:function name="reset_game">
    <q:set name="managers" value="{[]}" />
    <q:set name="jobs" value="{[]}" />
    <q:set name="retired" value="{[]}" />
    <q:set name="turn" value="{0}" />
    <q:set name="matchday" value="{0}" />
    <q:set name="season" value="{2026}" />
    <q:set name="champion" value="{-1}" />
    <q:set name="last" value="{[]}" />
    <q:set name="news" value="{[]}" />
  </q:function>

  <!-- an index of a list of weights, drawn by them -->
  <q:function name="roll" params="weights">
    <q:set name="total" value="{0}" />
    <q:loop items="{weights}" var="w"><q:set name="total" value="{total + w}" /></q:loop>
    <q:set name="r" value="{random(0, total)}" />
    <q:loop var="i" from="0" to="{len(weights) - 1}">
      <q:set name="r" value="{r - weights[i]}" />
      <q:if condition="{r <= 0}"><q:return value="{i}" /></q:if>
    </q:loop>
    <q:return value="{len(weights) - 1}" />
  </q:function>

  <!-- where an item is in a list (-1: not there) -->
  <q:function name="place_in" params="list, item">
    <q:loop var="k" from="0" to="{len(list) - 1}"><q:if condition="{list[k] == item}"><q:return value="{k}" /></q:if></q:loop>
    <q:return value="{-1}" />
  </q:function>

  <!-- how many times an item is in a list -->
  <q:function name="times_in" params="list, item">
    <q:set name="n" value="{0}" />
    <q:loop items="{list}" var="x"><q:if condition="{x == item}"><q:set name="n" value="{n + 1}" /></q:if></q:loop>
    <q:return value="{n}" />
  </q:function>

  <!-- the one after an item in a list, round to the first -->
  <q:function name="after_in" params="list, item">
    <q:return value="{list[(place_in(list, item) + 1) % len(list)]}" />
  </q:function>

  <!-- a list without one of its items -->
  <q:function name="without" params="list, item">
    <q:set name="out" value="{[]}" />
    <q:set name="gone" value="{false}" />
    <q:loop items="{list}" var="x">
      <q:if condition="{x == item and not gone}"><q:set name="gone" value="{true}" />
        <q:else><q:set name="out" value="{out + [x]}" /></q:else>
      </q:if>
    </q:loop>
    <q:return value="{out}" />
  </q:function>

  <!-- the manager playing now, their club -->
  <q:function name="my_club">
    <q:return value="{clubs[managers[turn].club]}" />
  </q:function>

  <!-- money as the papers write it: $1.500.000 -->
  <q:function name="money" params="n">
    <q:return value="{('-$' if n < 0 else '$') + thousands(abs(round(n)), '.')}" />
  </q:function>

  <!-- a bar of so many blocks: 0 to 100 -->
  <q:function name="blocks" params="n, width">
    <q:set name="full" value="{min(width, max(0, round(n * width / 100)))}" />
    <q:return value="{repeat('█', full) + repeat('░', width - full)}" />
  </q:function>

  <!-- what the papers say: a phrase, and what follows it as it is (a year, a club) -->
  <q:function name="said" params="text, arg">
    <q:set name="news" value="{[ {'text': text, 'arg': arg} ] + news}" />
  </q:function>

  <!-- ===== A new world (GAME_DESIGN v0.2: how clubs and players are made) ===== -->

  <!-- how many traits by band of strength: 0, 1, 2, 3 or 4 -->
  <q:function name="trait_count" params="strength">
    <q:if condition="{strength <= 20}"><q:return value="{roll([75, 22, 3, 0, 0])}" /></q:if>
    <q:if condition="{strength <= 30}"><q:return value="{roll([47, 38, 14, 1, 0])}" /></q:if>
    <q:if condition="{strength <= 40}"><q:return value="{roll([25, 40, 27, 8, 0])}" /></q:if>
    <q:return value="{roll([10, 33, 35, 14, 8])}" />
  </q:function>

  <!-- the traits: commons by position, one rare at most (one draw in three, or the slot the commons do not fill) -->
  <q:function name="traits_for" params="strength, pos">
    <q:set name="n" value="{trait_count(strength)}" />
    <q:set name="commons" value="{ {'GK': ['Wall', 'Leader'], 'DF': ['Set pieces', 'Leader', 'Wall'], 'MF': ['Finisher', 'Set pieces', 'Leader'], 'FW': ['Finisher', 'Set pieces', 'Leader']}[pos] }" />
    <q:set name="out" value="{[]}" />
    <q:if condition="{n > 0 and pos != 'GK' and (chance(1 / 3) or n > len(commons))}">
      <q:set name="out" value="{[pick(['Ace', 'Star'])]}" />
    </q:if>
    <q:loop var="k" from="1" to="{n}">
      <q:if condition="{len(out) < n and len(commons) > 0}">
        <q:set name="c" value="{pick(commons)}" />
        <q:set name="out" value="{out + [c]}" />
        <q:set name="commons" value="{without(commons, c)}" />
      </q:if>
    </q:loop>
    <q:return value="{out}" />
  </q:function>

  <!-- a second position, as versatile as the player is good -->
  <q:function name="secondary" params="strength, pos">
    <q:set name="near" value="{ {'GK': [], 'DF': ['MF'], 'MF': ['DF', 'FW'], 'FW': ['MF']}[pos] }" />
    <q:set name="n" value="{roll([70, 25, 5]) if strength <= 25 else (roll([40, 40, 20]) if strength <= 35 else roll([20, 50, 30]))}" />
    <q:set name="out" value="{[]}" />
    <q:loop var="k" from="1" to="{n}">
      <q:if condition="{len(near) > 0}">
        <q:set name="c" value="{pick(near)}" />
        <q:set name="out" value="{out + [c]}" />
        <q:set name="near" value="{without(near, c)}" />
      </q:if>
    </q:loop>
    <q:return value="{out}" />
  </q:function>

  <!-- a name no one else of the world has (a Bambuzinho in three clubs was three players of one name): a nickname,
       an initial, or a first name and a surname -->
  <q:function name="player_name" params="taken">
    <q:loop var="k" from="1" to="20">
      <q:set name="drawn" value="{pick(first_names) + ' ' + pick(surnames)}" />
      <q:if condition="{chance(0.2)}"><q:set name="drawn" value="{pick(nicknames)}" />
        <q:elseif condition="{chance(0.12)}"><q:set name="drawn" value="{pick(first_names) + ' ' + pick(surnames)[0] + '.'}" /></q:elseif>
      </q:if>
      <q:if condition="{not (drawn in taken)}"><q:return value="{drawn}" /></q:if>
    </q:loop>
    <q:loop items="{[' Jr.', ' Neto', ' II', ' III', ' Filho']}" var="kin">   <!-- a name taken twenty times over: a son's -->
      <q:if condition="{not ((drawn + kin) in taken)}"><q:return value="{drawn + kin}" /></q:if>
    </q:loop>
    <q:return value="{drawn + ' ' + str(len(taken))}" />
  </q:function>

  <!-- traits as one would count them: a genius is two -->
  <q:function name="weight" params="p">
    <q:return value="{len(p.traits) + (2 if p.genius else 0)}" />
  </q:function>

  <!-- the month's salary: strength² × 15, give or take a fifth, times what the traits are worth -->
  <q:function name="salary_of" params="p">
    <q:set name="times" value="{[1.0, 1.3, 1.75, 3.25, 6.0, 10.0][min(5, weight(p))]}" />
    <q:return value="{p.strength * p.strength * 15 * random(0.8, 1.2) * times}" />
  </q:function>

  <q:function name="new_player" params="strength, pos, num, taken">
    <q:set name="p" value="{ {'name': player_name(taken), 'num': num, 'pos': pos, 'sec': secondary(strength, pos), 'strength': strength, 'traits': traits_for(strength, pos), 'genius': false, 'morale': 70, 'form': 100, 'salary': 0, 'goals': 0, 'yellows': 0, 'reds': 0, 'injured': 0, 'suspended': 0, 'xi': '', 'bench': false, 'played': 0, 'booked': false, 'off': '', 'start': '', 'sat': false} }" />
    <q:set name="p.salary" value="{salary_of(p)}" />
    <q:return value="{p}" />
  </q:function>

  <!-- a club of a division (1 to 4): its 22 by the design's spread of strength for it, its ground and its purse -->
  <q:function name="new_club" params="i, div, known">
    <q:set name="rows" value="{[[[3, 42, 50], [11, 35, 44], [8, 28, 38]], [[2, 35, 42], [10, 28, 36], [10, 22, 30]], [[1, 30, 35], [9, 24, 32], [12, 15, 26]], [[1, 25, 28], [8, 18, 26], [13, 8, 20]]][div - 1]}" />
    <q:set name="strengths" value="{[]}" />
    <q:loop items="{rows}" var="row">
      <q:loop var="k" from="1" to="{row[0]}"><q:set name="strengths" value="{strengths + [round(random(row[1], row[2]))]}" /></q:loop>
    </q:loop>
    <q:set name="strengths" value="{sort(strengths, true)}" />
    <q:set name="places" value="{['GK', 'GK', 'DF', 'DF', 'DF', 'DF', 'DF', 'DF', 'DF', 'DF', 'MF', 'MF', 'MF', 'MF', 'MF', 'MF', 'MF', 'MF', 'FW', 'FW', 'FW', 'FW']}" />
    <q:set name="players" value="{[]}" />
    <q:set name="names" value="{known}" />
    <q:loop var="k" from="0" to="21">
      <q:set name="pos" value="{pick(places)}" />
      <q:set name="places" value="{without(places, pos)}" />
      <q:set name="p" value="{new_player(strengths[k], pos, k + 1, names)}" />
      <q:set name="players" value="{players + [p]}" />
      <q:set name="names" value="{names + [p.name]}" />
    </q:loop>
    <q:set name="capacity" value="{round(random([30000, 15000, 8000, 5000][div - 1], [50000, 30000, 15000, 8000][div - 1]) / 500) * 500}" />
    <q:return value="{ {'name': club_names[i], 'short': club_short[i], 'div': div, 'players': players, 'capacity': capacity, 'ticket': 15, 'balance': random([500000, 200000, 50000, 10000][div - 1], [2000000, 800000, 300000, 100000][div - 1]), 'points': 0, 'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 'gf': 0, 'ga': 0, 'form': [], 'manager': 0, 'formation': '4-4-2', 'style': 'Balanced', 'objective': 'Auto', 'plan': 'Draw', 'reactions': [], 'gate': 0, 'crowd': 0, 'wages': 0, 'history': [], 'expect': 5} }" />
  </q:function>

  <!-- the world's geniuses, three to five: the best of two to four clubs of the first division, and one hidden in the
       third or the fourth (strength 40-42) -->
  <q:function name="place_geniuses">
    <q:set name="big" value="{in_div(1)}" />
    <q:loop var="k" from="1" to="{round(random(2, 4))}">
      <q:set name="c" value="{pick(big)}" />
      <q:set name="big" value="{without(big, c)}" />
      <q:set name="star" value="{best(clubs[c].players)}" />
      <q:set name="star.genius" value="{true}" />
      <q:set name="star.strength" value="{max(star.strength, 43)}" />
      <q:set name="star.traits" value="{star.traits[0:3]}" />
      <q:set name="star.salary" value="{salary_of(star)}" />
    </q:loop>
    <q:set name="gem" value="{best(clubs[pick(in_div(3) + in_div(4))].players)}" />
    <q:set name="gem.genius" value="{true}" />
    <q:set name="gem.strength" value="{round(random(40, 42))}" />
    <q:set name="gem.traits" value="{gem.traits[0:3]}" />
    <!-- on a small club's contract: paid for its traits, as no one knows yet what it is -->
    <q:set name="gem.salary" value="{gem.strength * gem.strength * 15 * random(0.8, 1.2) * [1.0, 1.3, 1.75, 3.25][len(gem.traits)]}" />
  </q:function>

  <q:function name="best" params="players">
    <q:set name="top" value="{players[0]}" />
    <q:loop items="{players}" var="p"><q:if condition="{p.strength > top.strength}"><q:set name="top" value="{p}" /></q:if></q:loop>
    <q:return value="{top}" />
  </q:function>

  <!-- home and away, the circle way, each division on its own (its first club stays, the others turn): a round is
       the five matches of each division, the first division's first -->
  <q:function name="make_fixtures">
    <q:set name="fixtures" value="{[[], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []]}" />
    <q:loop var="d" from="1" to="4">
      <q:set name="order" value="{in_div(d)}" />
      <q:loop var="r" from="0" to="8">
        <q:set name="games" value="{[]}" />
        <q:set name="back" value="{[]}" />
        <q:loop var="i" from="0" to="4">
          <q:if condition="{(r + i) % 2 == 0}"><q:set name="games" value="{games + [[order[i], order[9 - i]]]}" /><q:set name="back" value="{back + [[order[9 - i], order[i]]]}" />
            <q:else><q:set name="games" value="{games + [[order[9 - i], order[i]]]}" /><q:set name="back" value="{back + [[order[i], order[9 - i]]]}" /></q:else>
          </q:if>
        </q:loop>
        <q:set name="fixtures" index="{r}" value="{fixtures[r] + games}" />
        <q:set name="fixtures" index="{r + 9}" value="{fixtures[r + 9] + back}" />
        <q:set name="order" value="{[order[0], order[9]] + order[1:9]}" />
      </q:loop>
    </q:loop>
  </q:function>

  <q:function name="new_world">
    <q:set name="clubs" value="{[]}" />
    <q:set name="known" value="{[]}" />
    <q:loop var="i" from="0" to="39">
      <q:set name="made" value="{new_club(i, floor(i / 10) + 1, known)}" />
      <q:set name="clubs" value="{clubs + [made]}" />
      <q:loop items="{made.players}" var="p"><q:set name="known" value="{known + [p.name]}" /></q:loop>
    </q:loop>
    <q:call function="place_geniuses" />
    <q:call function="make_fixtures" />
    <q:loop items="{managers}" var="m">
      <q:set name="c" value="{clubs[m.club]}" />
      <q:set name="c.manager" value="{1}" />
    </q:loop>
    <q:loop items="{clubs}" var="club"><q:call function="auto_lineup" args="{club}" /></q:loop>
    <q:call function="set_expectations" />
    <q:set name="matchday" value="{0}" />
    <q:call function="prepare_round" />
    <q:set name="news" value="{[]}" />
    <q:call function="said" args="{'The Panda League kicks off:'}, {str(season)}" />
  </q:function>

  <!-- ===== The divisions ===== -->

  <!-- the clubs of a division, by their number -->
  <q:function name="in_div" params="d">
    <q:set name="out" value="{[]}" />
    <q:loop var="i" from="0" to="{len(clubs) - 1}"><q:if condition="{clubs[i].div == d}"><q:set name="out" value="{out + [i]}" /></q:if></q:loop>
    <q:return value="{out}" />
  </q:function>

  <q:function name="div_name" params="d">
    <q:return value="{tr(['1st division', '2nd division', '3rd division', '4th division'][d - 1])}" />
  </q:function>

  <!-- what a division pays a month (GAME_DESIGN's quotas): the TV, the same to all; the sponsor, by the place (the
       top four, the middle, the two going down); and what a club costs: its staff and travel, and $1 a seat -->
  <q:function name="tv_of" params="club">
    <q:return value="{[500000, 200000, 50000, 20000][club.div - 1]}" />
  </q:function>

  <q:function name="sponsor_of" params="club, place">
    <q:return value="{[[300000, 150000, 50000], [150000, 75000, 25000], [70000, 35000, 12000], [30000, 15000, 5000]][club.div - 1][0 if place < 4 else (2 if place >= 8 else 1)]}" />
  </q:function>

  <q:function name="costs_of" params="club">
    <q:return value="{[100000, 70000, 40000, 20000][club.div - 1] + club.capacity}" />
  </q:function>

  <!-- ===== The career (GAME_DESIGN decision 21): the board's patience, the sack, the offers ===== -->

  <q:function name="new_career" params="club_name">
    <q:return value="{ {'seasons': 0, 'matches': 0, 'points': 0, 'titles': 0, 'ups': 0, 'downs': 0, 'sacked': 0, 'clubs': [club_name]} }" />
  </q:function>

  <!-- what a club's squad is worth: the mean of its sixteen strongest -->
  <q:function name="squad_strength" params="club">
    <q:set name="top" value="{[]}" />
    <q:loop items="{club.players}" var="p"><q:set name="top" value="{top + [p.strength]}" /></q:loop>
    <q:set name="best16" value="{sort(top, true)[0:16]}" />
    <q:set name="sum" value="{0}" />
    <q:loop items="{best16}" var="x"><q:set name="sum" value="{sum + x}" /></q:loop>
    <q:return value="{sum / 16}" />
  </q:function>

  <!-- what each board expects at the season's start: its squad's place among the division's squads -->
  <q:function name="set_expectations">
    <q:loop var="d" from="1" to="4">
      <q:set name="keys" value="{[]}" />
      <q:loop items="{in_div(d)}" var="i"><q:set name="keys" value="{keys + [[squad_strength(clubs[i]), 1000 - i]]}" /></q:loop>
      <q:set name="rank" value="{1}" />
      <q:loop items="{sort(keys, true)}" var="key">
        <q:set name="board" value="{clubs[1000 - key[1]]}" />
        <q:set name="board.expect" value="{rank}" />
        <q:set name="rank" value="{rank + 1}" />
      </q:loop>
    </q:loop>
  </q:function>

  <!-- after each round, each board: a win +3, a draw 0, a defeat -4, and half a point for each place above (or below)
       what it expects; a purse three months of wages in the red, -6 a round. At 0 the manager is sacked -->
  <q:function name="boards">
    <q:loop var="mi" from="0" to="{len(managers) - 1}">
      <q:set name="t" value="{managers[mi]}" />
      <q:set name="c" value="{clubs[t.club]}" />
      <q:set name="mark" value="{c.form[len(c.form) - 1] if len(c.form) > 0 else 'D'}" />
      <q:set name="t.career.matches" value="{t.career.matches + 1}" />
      <q:set name="t.career.points" value="{t.career.points + {'W': 3, 'D': 1, 'L': 0}[mark]}" />
      <q:set name="delta" value="{ {'W': 3, 'D': 0, 'L': -4}[mark] + 0.5 * (c.expect - position_of(t.club))}" />
      <q:if condition="{c.balance < -3 * payroll(c)}"><q:set name="delta" value="{delta - 6}" /></q:if>
      <q:set name="t.patience" value="{max(0, min(100, t.patience + delta))}" />
      <q:if condition="{t.patience <= 0 and not sacked_already(mi)}"><q:call function="sack" args="{mi}" /></q:if>
    </q:loop>
  </q:function>

  <q:function name="sacked_already" params="mi">
    <q:loop items="{jobs}" var="j"><q:if condition="{j.who == mi and j.kind == 'sacked'}"><q:return value="{true}" /></q:if></q:loop>
    <q:return value="{false}" />
  </q:function>

  <!-- the board has lost its patience: the club goes to the computer, and two clubs of the division below (or of the
       4th) that no manager has are offered; else, the career ends -->
  <q:function name="sack" params="mi">
    <q:set name="t" value="{managers[mi]}" />
    <q:set name="c" value="{clubs[t.club]}" />
    <q:set name="t.career.sacked" value="{t.career.sacked + 1}" />
    <q:call function="said" args="{'Sacked by the board of'}, {c.name + ': ' + t.name}" />
    <q:set name="jobs" value="{jobs + [ {'who': mi, 'kind': 'sacked', 'clubs': free_clubs(min(4, c.div + 1), t.club, 2), 'step': 0} ]}" />
  </q:function>

  <!-- so many clubs of a division no manager has, but one, drawn -->
  <q:function name="free_clubs" params="d, but, n">
    <q:set name="free" value="{[]}" />
    <q:loop items="{in_div(d)}" var="i"><q:if condition="{clubs[i].manager == 0 and i != but}"><q:set name="free" value="{free + [i]}" /></q:if></q:loop>
    <q:set name="out" value="{[]}" />
    <q:loop var="k" from="1" to="{n}">
      <q:if condition="{len(free) > 0}">
        <q:set name="drawn" value="{pick(free)}" />
        <q:set name="free" value="{without(free, drawn)}" />
        <q:set name="out" value="{out + [drawn]}" />
      </q:if>
    </q:loop>
    <q:return value="{out}" />
  </q:function>

  <!-- the season's verdict, before the clubs move: a board pleased by a place above what it expected (or the promotion)
       gains patience, and one let down loses it; a manager who went up, or finished three places above the board's
       hopes, will be offered two clubs of the division above the club's next one (drawn once the clubs have moved:
       draw_offers) -->
  <q:function name="season_verdicts" params="orders">
    <q:loop var="mi" from="0" to="{len(managers) - 1}">
      <q:set name="t" value="{managers[mi]}" />
      <q:set name="c" value="{clubs[t.club]}" />
      <q:set name="at" value="{place_in(orders[c.div - 1], t.club) + 1}" />
      <q:set name="up" value="{c.div > 1 and at <= 2}" />
      <q:set name="down" value="{c.div < 4 and at >= 9}" />
      <q:set name="t.career.seasons" value="{t.career.seasons + 1}" />
      <q:if condition="{at == 1}"><q:set name="t.career.titles" value="{t.career.titles + 1}" /></q:if>
      <q:if condition="{up}"><q:set name="t.career.ups" value="{t.career.ups + 1}" /></q:if>
      <q:if condition="{down}"><q:set name="t.career.downs" value="{t.career.downs + 1}" /></q:if>
      <q:set name="t.patience" value="{max(0, min(100, t.patience + 4 * (c.expect - at) + (20 if up else 0) - (30 if down else 0)))}" />
      <q:if condition="{t.patience <= 0 and not sacked_already(mi)}">
        <q:set name="t.career.sacked" value="{t.career.sacked + 1}" />
        <q:call function="said" args="{'Sacked by the board of'}, {c.name + ': ' + t.name}" />
        <q:set name="jobs" value="{jobs + [ {'who': mi, 'kind': 'sacked', 'clubs': [], 'step': 1} ]}" />
        <q:elseif condition="{up or c.expect - at >= 3}"><q:set name="jobs" value="{jobs + [ {'who': mi, 'kind': 'offer', 'clubs': [], 'step': -1} ]}" /></q:elseif>
      </q:if>
    </q:loop>
  </q:function>

  <!-- the season's jobs, once the clubs have moved: two clubs no manager has, of the division above the club's (an
       offer) or below it (the sack); an offer no club makes is no offer -->
  <q:function name="draw_offers">
    <q:set name="kept" value="{[]}" />
    <q:loop items="{jobs}" var="j">
      <q:if condition="{len(j.clubs) == 0 and j.step != 0}">
        <q:set name="j.clubs" value="{free_clubs(max(1, min(4, clubs[managers[j.who].club].div + j.step)), managers[j.who].club, 2)}" />
      </q:if>
      <q:if condition="{len(j.clubs) > 0 or j.kind == 'sacked'}"><q:set name="kept" value="{kept + [j]}" /></q:if>
    </q:loop>
    <q:set name="jobs" value="{kept}" />
  </q:function>

  <!-- a manager takes another club: the old one goes to the computer -->
  <q:function name="take_job" params="mi, club_index">
    <q:set name="t" value="{managers[mi]}" />
    <q:set name="old" value="{clubs[t.club]}" />
    <q:set name="old.manager" value="{0}" />
    <q:set name="old.objective" value="{'Auto'}" />
    <q:set name="new" value="{clubs[club_index]}" />
    <q:set name="new.manager" value="{1}" />
    <q:set name="t.club" value="{club_index}" />
    <q:set name="t.patience" value="{50}" />
    <q:set name="t.career.clubs" value="{t.career.clubs + [new.name]}" />
    <q:call function="said" args="{'New manager of'}, {new.name + ': ' + t.name}" />
  </q:function>

  <!-- a career ends: the club to the computer, the manager to the records -->
  <q:function name="end_career" params="mi">
    <q:set name="t" value="{managers[mi]}" />
    <q:set name="old" value="{clubs[t.club]}" />
    <q:set name="old.manager" value="{0}" />
    <q:set name="retired" value="{retired + [ {'name': t.name, 'career': t.career} ]}" />
    <q:set name="left" value="{[]}" />
    <q:loop var="k" from="0" to="{len(managers) - 1}"><q:if condition="{k != mi}"><q:set name="left" value="{left + [managers[k]]}" /></q:if></q:loop>
    <q:set name="managers" value="{left}" />
    <q:set name="turn" value="{0}" />
    <!-- the jobs still waiting name managers by their place: one after the leaver moves up a place -->
    <q:set name="still" value="{[]}" />
    <q:loop items="{jobs}" var="j"><q:if condition="{j.who != mi}"><q:set name="j.who" value="{j.who - 1 if j.who > mi else j.who}" /><q:set name="still" value="{still + [j]}" /></q:if></q:loop>
    <q:set name="jobs" value="{still}" />
  </q:function>

  <!-- ===== The line-up ===== -->

  <!-- a formation's shape: how many defenders, midfielders, forwards -->
  <q:function name="shape" params="formation">
    <q:return value="{ {'4-4-2': [4, 4, 2], '4-3-3': [4, 3, 3], '5-3-2': [5, 3, 2], '4-5-1': [4, 5, 1], '3-4-3': [3, 4, 3], '5-4-1': [5, 4, 1]}[formation] }" />
  </q:function>

  <q:function name="available" params="p">
    <q:return value="{p.injured == 0 and p.suspended == 0}" />
  </q:function>

  <!-- how well a player plays a place: their own 100%, a second one 80%, another 50% -->
  <q:function name="fit_for" params="p, place">
    <q:return value="{1.0 if p.pos == place else (0.8 if place in p.sec else 0.5)}" />
  </q:function>

  <!-- what a player plays at in a place: strength, an ace +12, a genius +25; morale a tenth either way, and how
       fresh: a tired player (form 40) plays a fifth worse than a rested one; a genius or an ace feels both by half -->
  <q:function name="eff" params="p, place">
    <q:set name="base" value="{p.strength + (12 if 'Ace' in p.traits else 0) + (25 if p.genius else 0)}" />
    <q:set name="mood" value="{(0.9 + 0.1 * p.morale / 100) * (0.7 + 0.3 * p.form / 100)}" />
    <q:if condition="{p.genius or 'Ace' in p.traits}"><q:set name="mood" value="{(mood + 1) / 2}" /></q:if>
    <q:return value="{base * fit_for(p, place) * mood}" />
  </q:function>

  <!-- the best eleven for the club's formation, picked again from the whole squad -->
  <q:function name="auto_lineup" params="club">
    <q:loop items="{club.players}" var="p"><q:set name="p.xi" value="{''}" /><q:set name="p.bench" value="{false}" /></q:loop>
    <q:call function="fill_lineup" args="{club}" />
  </q:function>

  <!-- the eleven's open places filled, and the bench up to seven: who cannot play leaves first, and who is in a
       place the formation does not have; each place by those who play it as their own first, then by those for
       whom it is a second position, then by anyone (a genius of the midfield plays in the midfield, not in goal
       because half of him beats the keeper). A manager's eleven stays as it is but for the gaps -->
  <q:function name="fill_lineup" params="club">
    <q:set name="n" value="{shape(club.formation)}" />
    <q:set name="open" value="{['GK'] + ['DF', 'DF', 'DF', 'DF', 'DF'][0:n[0]] + ['MF', 'MF', 'MF', 'MF', 'MF'][0:n[1]] + ['FW', 'FW', 'FW'][0:n[2]]}" />
    <q:loop items="{club.players}" var="p">
      <q:if condition="{not available(p)}"><q:set name="p.xi" value="{''}" /><q:set name="p.bench" value="{false}" /></q:if>
      <q:if condition="{p.xi != '' and p.xi in open}"><q:set name="open" value="{without(open, p.xi)}" /><q:set name="p.bench" value="{false}" />
        <q:elseif condition="{p.xi != ''}"><q:set name="p.xi" value="{''}" /></q:elseif>
      </q:if>
    </q:loop>
    <q:loop items="{[1.0, 0.8, 0.5]}" var="least">
      <q:loop items="{open}" var="place">
        <q:set name="top" value="{null}" />
        <q:loop items="{club.players}" var="p">
          <q:if condition="{p.xi == '' and available(p) and fit_for(p, place) >= least and (top == null or eff(p, place) > eff(top, place))}"><q:set name="top" value="{p}" /></q:if>
        </q:loop>
        <q:if condition="{top != null}"><q:set name="top.xi" value="{place}" /><q:set name="top.bench" value="{false}" /><q:set name="open" value="{without(open, place)}" /></q:if>
      </q:loop>
    </q:loop>
    <q:set name="seats" value="{0}" />
    <q:loop items="{club.players}" var="p"><q:if condition="{p.bench}"><q:set name="seats" value="{seats + 1}" /></q:if></q:loop>
    <q:loop var="k" from="{seats + 1}" to="7">
      <q:set name="top" value="{null}" />
      <q:loop items="{club.players}" var="p">
        <q:if condition="{p.xi == '' and not p.bench and available(p) and (top == null or p.strength > top.strength)}"><q:set name="top" value="{p}" /></q:if>
      </q:loop>
      <q:if condition="{top != null}"><q:set name="top.bench" value="{true}" /></q:if>
    </q:loop>
  </q:function>

  <!-- who is on the pitch: the eleven, less who was sent off, carried off or taken off -->
  <q:function name="on_pitch" params="club">
    <q:set name="out" value="{[]}" />
    <q:loop items="{club.players}" var="p"><q:if condition="{p.xi != '' and p.off == ''}"><q:set name="out" value="{out + [p]}" /></q:if></q:loop>
    <q:return value="{out}" />
  </q:function>

  <q:function name="eleven" params="club">
    <q:set name="out" value="{[]}" />
    <q:loop items="{club.players}" var="p"><q:if condition="{p.xi != ''}"><q:set name="out" value="{out + [p]}" /></q:if></q:loop>
    <q:return value="{out}" />
  </q:function>

  <!-- eleven who can play, one of them in goal -->
  <q:function name="lineup_ok" params="club">
    <q:set name="keepers" value="{0}" />
    <q:set name="out" value="{0}" />
    <q:loop items="{eleven(club)}" var="p">
      <q:if condition="{p.xi == 'GK'}"><q:set name="keepers" value="{keepers + 1}" /></q:if>
      <q:if condition="{not available(p)}"><q:set name="out" value="{out + 1}" /></q:if>
    </q:loop>
    <q:return value="{len(eleven(club)) == 11 and keepers == 1 and out == 0}" />
  </q:function>

  <!-- ===== Tactics (GAME_DESIGN v0.2: formations, styles and the counter-tactics) ===== -->

  <!-- a formation's lean, attack and defence -->
  <q:function name="lean" params="formation">
    <q:return value="{ {'4-4-2': [1.0, 1.0], '4-3-3': [1.06, 0.96], '5-3-2': [0.95, 1.07], '4-5-1': [0.93, 1.04], '3-4-3': [1.1, 0.9], '5-4-1': [0.88, 1.1]}[formation] }" />
  </q:function>

  <!-- a style's change to attack and defence -->
  <q:function name="mods" params="style">
    <q:return value="{ {'Balanced': [0, 0], 'Attacking': [0.15, -0.1], 'All-out attack': [0.3, -0.2], 'Defensive': [-0.1, 0.15], 'Park the bus': [-0.2, 0.3], 'Counter-attack': [0, 0.05], 'Kamikaze': [0.5, -0.4]}[style] }" />
  </q:function>

  <!-- a style's family: attacking, defensive, counter-attacking, balanced -->
  <q:function name="family" params="style">
    <q:return value="{ {'Balanced': 'B', 'Attacking': 'A', 'All-out attack': 'A', 'Kamikaze': 'A', 'Defensive': 'D', 'Park the bus': 'D', 'Counter-attack': 'C'}[style] }" />
  </q:function>

  <!-- the counter-tactics: what one family of styles gains against another -->
  <q:function name="edge" params="mine, theirs">
    <q:return value="{ {'AA': 0, 'AD': 0.1, 'AC': -0.15, 'AB': 0.05, 'DA': -0.1, 'DD': 0, 'DC': 0.1, 'DB': 0, 'CA': 0.15, 'CD': -0.1, 'CC': 0, 'CB': 0.05, 'BA': -0.05, 'BD': 0, 'BC': -0.05, 'BB': 0}[family(mine) + family(theirs)] }" />
  </q:function>

  <!-- how fast a style makes a match, for both sides: a side that sits back makes fewer chances at both ends
       (fewer goals, more draws); one that throws everyone forward makes more -->
  <q:function name="tempo" params="style">
    <q:return value="{ {'Balanced': 1.0, 'Attacking': 1.05, 'All-out attack': 1.1, 'Kamikaze': 1.18, 'Defensive': 0.88, 'Park the bus': 0.75, 'Counter-attack': 0.95}[style] }" />
  </q:function>

  <!-- the style a club tends to start with: of its last five matches, the family it started most with (of a tie,
       the latest), as it last played it; Balanced before its first match -->
  <q:function name="usual" params="club">
    <q:if condition="{len(club.history) == 0}"><q:return value="{'Balanced'}" /></q:if>
    <q:set name="fams" value="{[]}" />
    <q:loop items="{club.history}" var="h"><q:set name="fams" value="{fams + [family(h.style)]}" /></q:loop>
    <q:set name="top" value="{club.history[0].style}" />
    <q:loop items="{club.history}" var="h"><q:if condition="{times_in(fams, family(h.style)) > times_in(fams, family(top))}"><q:set name="top" value="{h.style}" /></q:if></q:loop>
    <q:return value="{top}" />
  </q:function>

  <!-- an objective's tactics against the style the opponent tends to start with: the start, and what to change
       to when winning, drawing or losing after a minute (the first due of each, in order) -->
  <q:function name="preset" params="club, objective, theirs">
    <q:set name="club.objective" value="{objective}" />
    <q:set name="fam" value="{family(theirs)}" />
    <q:if condition="{objective == 'Win'}">
      <q:set name="club.formation" value="{'4-3-3'}" /><q:set name="club.style" value="{'Balanced' if fam == 'C' else 'Attacking'}" />
      <q:set name="club.reactions" value="{[ {'when': 'winning', 'after': 75, 'formation': '4-4-2', 'style': 'Balanced'}, {'when': 'drawing', 'after': 60, 'formation': '3-4-3', 'style': 'All-out attack'}, {'when': 'losing', 'after': 60, 'formation': '3-4-3', 'style': 'All-out attack'}, {'when': 'losing', 'after': 80, 'formation': '3-4-3', 'style': 'Kamikaze'} ]}" />
      <q:elseif condition="{objective == 'Draw'}">
        <q:set name="club.formation" value="{'4-5-1'}" /><q:set name="club.style" value="{'Counter-attack' if fam == 'A' else 'Defensive'}" />
        <q:set name="club.reactions" value="{[ {'when': 'winning', 'after': 60, 'formation': '5-4-1', 'style': 'Park the bus'}, {'when': 'drawing', 'after': 70, 'formation': '5-4-1', 'style': 'Defensive'}, {'when': 'losing', 'after': 70, 'formation': '4-4-2', 'style': 'Balanced'}, {'when': 'losing', 'after': 82, 'formation': '4-3-3', 'style': 'Attacking'} ]}" />
      </q:elseif>
      <q:elseif condition="{objective == 'Avoid defeat'}">
        <q:set name="club.formation" value="{'5-4-1'}" /><q:set name="club.style" value="{'Counter-attack' if fam == 'A' else ('Defensive' if fam == 'C' else 'Park the bus')}" />
        <q:set name="club.reactions" value="{[ {'when': 'winning', 'after': 60, 'formation': '5-4-1', 'style': 'Park the bus'}, {'when': 'losing', 'after': 75, 'formation': '4-4-2', 'style': 'Attacking'}, {'when': 'losing', 'after': 85, 'formation': '3-4-3', 'style': 'Kamikaze'} ]}" />
      </q:elseif>
      <q:elseif condition="{objective == 'By hand'}">
        <q:set name="club.formation" value="{'4-4-2'}" /><q:set name="club.style" value="{'Balanced'}" />
        <q:set name="club.reactions" value="{[]}" />
      </q:elseif>
    </q:if>
  </q:function>

  <!-- a club's tactics for its next match: the computer's, and a manager's on Auto, by the opponent's strength; a manager's
       objective from its start again (what the last match changed is undone); by hand as left. The computer picks
       its eleven again (the rested come back, the tired rest); a manager's eleven stays, its gaps filled -->
  <q:function name="ready" params="club, opponent, home">
    <q:set name="auto" value="{club.manager > 0 and club.objective == 'Auto'}" />
    <q:set name="club.plan" value="{auto_objective(club, opponent, home) if club.manager == 0 or auto else club.objective}" />
    <!-- a manager's objective reads the style the opponent tends to start with; the computer plays its objective's
         own, as Elifoot's did: it can be read, and beaten (when both sides read each other, the weaker side
         counters the stronger every time, and wins one match in three) -->
    <q:if condition="{club.plan != 'By hand'}"><q:call function="preset" args="{club}, {club.plan}, {usual(opponent) if club.manager > 0 else 'Balanced'}" /></q:if>
    <q:if condition="{auto}"><q:set name="club.objective" value="{'Auto'}" /></q:if>
    <q:if condition="{club.manager == 0}"><q:call function="auto_lineup" args="{club}" />
      <q:else><q:call function="fill_lineup" args="{club}" /></q:else>
    </q:if>
  </q:function>

  <!-- Auto: the objective a manager would pick against this opponent, here or away -->
  <q:function name="auto_objective" params="club, opponent, home">
    <q:set name="mine" value="{rating(club)}" />
    <q:set name="theirs" value="{rating(opponent)}" />
    <q:if condition="{mine > theirs * 1.08 or (home and mine > theirs * 0.97)}"><q:return value="{'Win'}" /></q:if>
    <q:if condition="{mine < theirs * 0.85}"><q:return value="{'Avoid defeat'}" /></q:if>
    <q:return value="{'Draw'}" />
  </q:function>

  <!-- how strong a club's eleven is, whatever its formation: attack and defence without the formation's lean (the
       objective picked by it does not change the objective again) -->
  <q:function name="rating" params="club">
    <q:set name="pw" value="{power(club)}" />
    <q:return value="{pw[0] / lean(club.formation)[0] + pw[1] / lean(club.formation)[1]}" />
  </q:function>

  <!-- a club's attack and defence as it lines up (in a match, as it stands on the pitch): the forwards and midfielders attack, the keeper, the defence and the midfield defend -->
  <q:function name="power" params="club">
    <q:set name="sums" value="{ {'GK': 0, 'DF': 0, 'MF': 0, 'FW': 0} }" />
    <q:set name="counts" value="{ {'GK': 0, 'DF': 0, 'MF': 0, 'FW': 0} }" />
    <q:set name="walls" value="{0}" />
    <q:set name="leader" value="{false}" />
    <q:set name="xi" value="{on_pitch(club)}" />
    <q:loop items="{xi}" var="p">
      <q:set name="sums" index="{p.xi}" value="{sums[p.xi] + eff(p, p.xi)}" />
      <q:set name="counts" index="{p.xi}" value="{counts[p.xi] + 1}" />
      <q:if condition="{'Wall' in p.traits and (p.xi == 'GK' or p.xi == 'DF')}"><q:set name="walls" value="{walls + 1}" /></q:if>
      <q:if condition="{'Leader' in p.traits}"><q:set name="leader" value="{true}" /></q:if>
    </q:loop>
    <q:set name="avg" value="{ {'GK': sums['GK'] / max(1, counts['GK']), 'DF': sums['DF'] / max(1, counts['DF']), 'MF': sums['MF'] / max(1, counts['MF']), 'FW': sums['FW'] / max(1, counts['FW'])} }" />
    <q:if condition="{counts['GK'] == 0}"><q:set name="avg" index="{'GK'}" value="{avg['DF'] * 0.5}" /></q:if>   <!-- an outfield player in goal -->
    <q:set name="att" value="{avg['FW'] * 0.55 + avg['MF'] * 0.45}" />
    <q:set name="dfn" value="{(avg['DF'] * 0.5 + avg['GK'] * 0.3 + avg['MF'] * 0.2) * (1 + 0.06 * walls)}" />
    <q:set name="lift" value="{(1.04 if leader else 1.0) * (1 - 0.08 * max(0, 11 - len(xi)))}" />   <!-- a man short: 8% weaker -->
    <q:return value="{[att * lift * lean(club.formation)[0], dfn * lift * lean(club.formation)[1]]}" />
  </q:function>

  <!-- ===== The live round (GAME_DESIGN v0.2: the live round, every match in the same minute) ===== -->

  <!-- the share of a ground that would come at $15: the table, the visitor, the form, a star in the eleven; a dearer
       ticket keeps people away (at $30 two in five of them come, at $50 one in five). And the day: the weather, the
       traffic, what else is on (`day`, 0.85 to 1.15 a match), so a price says about how many, never exactly -->
  <q:function name="crowd_for" params="home, away_place, place, day">
    <q:set name="want" value="{0.55 + 0.25 * (4.5 - place) / 4.5 + 0.15 * max(0, 4.5 - away_place) / 4.5 + 0.04 * times_in(home.form, 'W') - 0.04 * times_in(home.form, 'L')}" />
    <q:set name="star" value="{false}" />
    <q:loop items="{eleven(home)}" var="p"><q:if condition="{'Star' in p.traits}"><q:set name="star" value="{true}" /></q:if></q:loop>
    <q:set name="want" value="{max(0.15, want + (0.12 if star else 0))}" />
    <q:return value="{min(home.capacity, round(home.capacity * want * day * (15 / home.ticket) ** 1.3))}" />
  </q:function>

  <!-- a side of a match: its club, attack and defence with its style; the counter-tactics lift or sink both; the
       home side is lifted by its ground (4%) and by its crowd, up to a quarter more with the ground full -->
  <q:function name="side" params="club, other, home, fill">
    <q:set name="mine" value="{power(club)}" />
    <q:set name="m" value="{mods(club.style)}" />
    <q:set name="e" value="{edge(club.style, other.style)}" />
    <q:set name="h" value="{1.08 + 0.25 * fill if home else 1.0}" />
    <q:return value="{ {'attack': mine[0] * (1 + m[0]) * (1 + e) * h, 'defense': mine[1] * (1 + m[1]) * (1 + e) * h, 'shots': 0, 'on': 0, 'press': 0, 'subs': 0, 'done': []} }" />
  </q:function>

  <!-- the round's matches as they kick off: the crowd, the eleven as it starts (a manager's comes back to it after
       the match) -->
  <q:function name="kickoff">
    <q:set name="matches" value="{[]}" />
    <q:set name="orders" value="{[table_order(1), table_order(2), table_order(3), table_order(4)]}" />
    <q:loop items="{fixtures[matchday]}" var="g">
      <q:set name="home" value="{clubs[g[0]]}" />
      <q:set name="away" value="{clubs[g[1]]}" />
      <!-- the tactics and the elevens were made ready after the last round (prepare_round), or by the manager since:
           what the dashboard shows is what plays; only a manager's gaps are filled -->
      <q:if condition="{home.manager > 0}"><q:call function="fill_lineup" args="{home}" /></q:if>
      <q:if condition="{away.manager > 0}"><q:call function="fill_lineup" args="{away}" /></q:if>
      <q:loop items="{home.players + away.players}" var="p"><q:set name="p.start" value="{p.xi}" /><q:set name="p.sat" value="{p.bench}" /><q:set name="p.off" value="{''}" /><q:set name="p.booked" value="{false}" /></q:loop>
      <q:set name="order" value="{orders[home.div - 1]}" />
      <q:set name="crowd" value="{crowd_for(home, place_in(order, g[1]), place_in(order, g[0]), random(0.85, 1.15))}" />
      <q:set name="fill" value="{crowd / home.capacity}" />
      <q:set name="matches" value="{matches + [ {'home': g[0], 'away': g[1], 'hg': 0, 'ag': 0, 'events': [], 'h': side(home, away, true, fill), 'a': side(away, home, false, fill), 'styles': [home.style, away.style], 'crowd': crowd, 'fill': fill, 'luck': [random(0.8, 1.2), random(0.8, 1.2)]} ]}" />
    </q:loop>
    <q:return value="{matches}" />
  </q:function>

  <!-- who scores: the forwards most, the midfield some, a defender rarely; a finisher half again, a genius thrice -->
  <q:function name="scorer" params="club">
    <q:set name="xi" value="{on_pitch(club)}" />
    <q:set name="weights" value="{[]}" />
    <q:loop items="{xi}" var="p">
      <q:set name="w" value="{ {'GK': 0, 'DF': 1, 'MF': 3, 'FW': 6}[p.xi] * p.strength / 30 * (1.5 if 'Finisher' in p.traits else 1) * (3 if p.genius else 1)}" />
      <q:set name="weights" value="{weights + [w]}" />
    </q:loop>
    <q:return value="{xi[roll(weights)]}" />
  </q:function>

  <!-- a minute of a match: each side may make a chance, as many as the two styles make the match; a chance may be
       a goal. Strength counts to the power of seven tenths: the better side wins more, not always (a side weaker
       by 3 or more wins about one match in five). A booked player is more careful, but a second yellow is a red;
       a knock takes a player off (a tired one gets hurt more), and the best of the bench for the place comes on
       if three have not come on yet -->
  <q:function name="play_minute" params="m, minute">
    <q:set name="goals" value="{0}" />
    <q:set name="pace_of" value="{tempo(clubs[m.home].style) * tempo(clubs[m.away].style)}" />
    <q:loop items="{['h', 'a']}" var="s">
      <q:set name="me_side" value="{m[s]}" />
      <q:set name="them" value="{m['a' if s == 'h' else 'h']}" />
      <q:set name="club" value="{clubs[m.home if s == 'h' else m.away]}" />
      <q:set name="luck" value="{m.luck[0 if s == 'h' else 1]}" />
      <q:set name="att" value="{me_side.attack ** 0.7}" />
      <q:set name="dfn" value="{them.defense ** 0.7}" />
      <q:set name="me_side.press" value="{me_side.press * 0.8}" />   <!-- the chances of the last minutes, the older ones fading -->
      <q:if condition="{chance(0.12 * att / (att + dfn) * luck * pace_of)}">
        <q:set name="me_side.shots" value="{me_side.shots + 1}" />
        <q:set name="me_side.press" value="{me_side.press + 1}" />
        <q:set name="in_net" value="{chance(0.27 * sqrt(att / dfn))}" />
        <q:if condition="{in_net or chance(0.4)}"><q:set name="me_side.on" value="{me_side.on + 1}" /></q:if>   <!-- on target: a goal, or the keeper saved it -->
        <q:if condition="{in_net}">
          <q:set name="p" value="{scorer(club)}" />
          <q:set name="p.goals" value="{p.goals + 1}" />
          <q:if condition="{s == 'h'}"><q:set name="m.hg" value="{m.hg + 1}" /><q:else><q:set name="m.ag" value="{m.ag + 1}" /></q:else></q:if>
          <q:set name="m.events" value="{[ {'kind': 'goal', 'minute': minute, 'who': p.name, 'club': club.short} ] + m.events}" />
          <q:set name="goals" value="{goals + 1}" />
        </q:if>
      </q:if>
      <q:set name="xi" value="{on_pitch(club)}" />
      <q:set name="card" value="{'yellow' if chance(0.02) else ('red' if chance(0.0002) else '')}" />
      <q:if condition="{card == 'yellow'}">
        <q:set name="weights" value="{[]}" />
        <q:loop items="{xi}" var="q"><q:set name="weights" value="{weights + [0.5 if q.booked else 1]}" /></q:loop>
        <q:set name="p" value="{xi[roll(weights)]}" />
        <q:if condition="{p.booked}">
          <q:set name="card" value="{'second'}" />
          <q:set name="p.yellows" value="{p.yellows - 1}" />   <!-- the yellows of a red do not count towards a ban of three -->
          <q:else>
            <q:set name="p.booked" value="{true}" />
            <q:set name="p.yellows" value="{p.yellows + 1}" />
            <q:set name="m.events" value="{[ {'kind': 'card', 'minute': minute, 'who': p.name, 'club': club.short} ] + m.events}" />
          </q:else>
        </q:if>
      </q:if>
      <q:if condition="{card == 'red'}"><q:set name="p" value="{pick(xi)}" /></q:if>
      <q:if condition="{card == 'red' or card == 'second'}">
        <q:set name="p.off" value="{'red'}" />
        <q:set name="p.reds" value="{p.reds + 1}" />
        <q:set name="m.events" value="{[ {'kind': 'red', 'minute': minute, 'who': p.name, 'club': club.short} ] + m.events}" />
        <q:call function="refresh" args="{m}, {s}" />
      </q:if>
      <q:set name="xi" value="{on_pitch(club)}" />
      <q:if condition="{chance(0.0015 * len(xi) / 11)}">
        <q:set name="weights" value="{[]}" />
        <q:loop items="{xi}" var="q"><q:set name="weights" value="{weights + [1 + max(0, 80 - q.form) / 40]}" /></q:loop>
        <q:set name="p" value="{xi[roll(weights)]}" />
        <q:set name="p.off" value="{'injured'}" />
        <q:set name="p.injured" value="{round(random(1, 4))}" />
        <q:set name="m.events" value="{[ {'kind': 'knock', 'minute': minute, 'who': p.name, 'club': club.short} ] + m.events}" />
        <q:set name="on" value="{best_on_bench(club, p.xi)}" />
        <q:if condition="{on != null and m[s].subs < 3}"><q:call function="bring_on" args="{m}, {s}, {p}, {on}, {minute}" /></q:if>
        <q:call function="refresh" args="{m}, {s}" />
      </q:if>
    </q:loop>
    <q:return value="{goals}" />
  </q:function>

  <!-- a match in numbers: the shots (on target), the ball (by how the sides attack) and who is pressing (the chances
       of the last minutes): Shots 7 (3) x 4 (1)   Ball 54% x 46%   Pressing: LON ▶▶ -->
  <q:function name="stats_line" params="m">
    <q:set name="ha" value="{m.h.attack ** 0.7}" />
    <q:set name="aa" value="{m.a.attack ** 0.7}" />
    <q:set name="ball" value="{round(100 * ha / (ha + aa))}" />
    <q:set name="lead" value="{m.h.press - m.a.press}" />
    <q:set name="who" value="{'=' if abs(lead) < 0.5 else (clubs[m.home].short + ' ' + repeat('▶', min(3, ceil(lead))) if lead > 0 else clubs[m.away].short + ' ' + repeat('◀', min(3, ceil(-lead))))}" />
    <q:return value="{shots_line(m) + '   ' + tr('Ball') + ' ' + str(ball) + '% x ' + str(100 - ball) + '%   ' + tr('Pressing:') + ' ' + who}" />
  </q:function>

  <q:function name="shots_line" params="m">
    <q:return value="{tr('Shots') + ' ' + str(m.h.shots) + ' (' + str(m.h.on) + ') x ' + str(m.a.shots) + ' (' + str(m.a.on) + ')'}" />
  </q:function>

  <!-- the best of the bench for a place (null: no one left to come on) -->
  <q:function name="best_on_bench" params="club, place">
    <q:set name="top" value="{null}" />
    <q:loop items="{club.players}" var="q">
      <q:if condition="{q.bench and q.xi == '' and q.off == '' and available(q) and (top == null or eff(q, place) > eff(top, place))}"><q:set name="top" value="{q}" /></q:if>
    </q:loop>
    <q:return value="{top}" />
  </q:function>

  <!-- a substitution: who leaves stays off (taken off, or carried off), who comes on takes the place -->
  <q:function name="bring_on" params="m, s, leaving, coming, minute">
    <q:set name="club" value="{clubs[m.home if s == 'h' else m.away]}" />
    <q:if condition="{leaving.off == ''}"><q:set name="leaving.off" value="{'subbed'}" /></q:if>
    <q:set name="coming.xi" value="{leaving.xi}" />
    <q:set name="coming.bench" value="{false}" />
    <q:set name="m_side" value="{m[s]}" />
    <q:set name="m_side.subs" value="{m_side.subs + 1}" />
    <q:set name="m.events" value="{[ {'kind': 'sub', 'minute': minute, 'who': coming.name, 'out': leaving.name, 'club': club.short} ] + m.events}" />
  </q:function>

  <!-- a side's attack and defence again, as it stands now (a red, a substitution, a change of tactics) -->
  <q:function name="refresh" params="m, s">
    <q:set name="club" value="{clubs[m.home if s == 'h' else m.away]}" />
    <q:set name="other" value="{clubs[m.away if s == 'h' else m.home]}" />
    <q:set name="fresh" value="{side(club, other, s == 'h', m.fill)}" />
    <q:set name="fresh.shots" value="{m[s].shots}" />
    <q:set name="fresh.on" value="{m[s].on}" />
    <q:set name="fresh.press" value="{m[s].press}" />
    <q:set name="fresh.subs" value="{m[s].subs}" />
    <q:set name="fresh.done" value="{m[s].done}" />
    <q:set name="m" index="{s}" value="{fresh}" />
  </q:function>

  <!-- how a side stands: winning, drawing, losing -->
  <q:function name="standing" params="m, s">
    <q:set name="mine" value="{m.hg if s == 'h' else m.ag}" />
    <q:set name="theirs" value="{m.ag if s == 'h' else m.hg}" />
    <q:return value="{'winning' if mine > theirs else ('drawing' if mine == theirs else 'losing')}" />
  </q:function>

  <!-- a reaction due now: the first of the club's not done yet whose time and score have come -->
  <q:function name="due" params="m, s, minute">
    <q:set name="club" value="{clubs[m.home if s == 'h' else m.away]}" />
    <q:loop var="k" from="0" to="{len(club.reactions) - 1}">
      <q:set name="r" value="{club.reactions[k]}" />
      <q:if condition="{minute >= r.after and r.when == standing(m, s) and not (k in m[s].done)}"><q:return value="{k}" /></q:if>
    </q:loop>
    <q:return value="{-1}" />
  </q:function>

  <!-- a change of tactics during a match: the side's attack and defence again -->
  <q:function name="change" params="m, s, formation, style">
    <q:set name="club" value="{clubs[m.home if s == 'h' else m.away]}" />
    <q:set name="club.formation" value="{formation}" />
    <q:set name="club.style" value="{style}" />
    <q:call function="refresh" args="{m}, {s}" />
    <q:set name="m.events" value="{[ {'kind': 'tactic', 'club': club.short, 'formation': formation, 'style': style} ] + m.events}" />
  </q:function>

  <!-- a line of a match's events, in the player's language -->
  <q:function name="event_text" params="e">
    <q:if condition="{e.kind == 'tactic'}"><q:return value="{'⚙    ' + e.club + ': ' + e.formation + ' ' + tr(e.style)}" /></q:if>
    <q:set name="at" value="{fit(str(e.minute), 2, 'right') + '′ ' + e.who + ' (' + e.club + ')'}" />
    <q:if condition="{e.kind == 'goal'}"><q:return value="{fit(tr('GOAL'), 5) + at}" /></q:if>
    <q:if condition="{e.kind == 'card'}"><q:return value="{'▮    ' + at}" /></q:if>
    <q:if condition="{e.kind == 'red'}"><q:return value="{'▮▮   ' + at + ' ' + tr('sent off')}" /></q:if>
    <q:if condition="{e.kind == 'sub'}"><q:return value="{'⇄    ' + at + ' ' + tr('for') + ' ' + e.out}" /></q:if>
    <q:return value="{'✚    ' + at + ' ' + tr('injured')}" />
  </q:function>

  <!-- the colour of an event's line -->
  <q:function name="event_color" params="e">
    <q:return value="{ {'goal': '#ffff55', 'card': '#ffff55', 'red': '#ff5555', 'knock': '#ff5555', 'sub': '#55ff55', 'tactic': '#55ffff'}[e.kind] }" />
  </q:function>

  <!-- ===== After the round ===== -->

  <!-- a division's table: its clubs by points, goal difference, goals -->
  <q:function name="table_order" params="d">
    <q:set name="keys" value="{[]}" />
    <q:loop var="i" from="0" to="{len(clubs) - 1}">
      <q:set name="c" value="{clubs[i]}" />
      <q:if condition="{c.div == d}"><q:set name="keys" value="{keys + [[c.points, c.gf - c.ga, c.gf, 1000 - i]]}" /></q:if>
    </q:loop>
    <q:set name="out" value="{[]}" />
    <q:loop items="{sort(keys, true)}" var="k"><q:set name="out" value="{out + [1000 - k[3]]}" /></q:loop>
    <q:return value="{out}" />
  </q:function>

  <q:function name="position_of" params="club_index">
    <q:return value="{place_in(table_order(clubs[club_index].div), club_index) + 1}" />
  </q:function>

  <!-- the round's results into the table, the players and the purses -->
  <q:function name="finish_round" params="matches">
    <q:set name="orders" value="{[table_order(1), table_order(2), table_order(3), table_order(4)]}" />
    <q:loop items="{matches}" var="m">
      <q:call function="result" args="{clubs[m.home]}, {m.hg}, {m.ag}" />
      <q:call function="result" args="{clubs[m.away]}, {m.ag}, {m.hg}" />
      <q:set name="home" value="{clubs[m.home]}" />
      <q:set name="away" value="{clubs[m.away]}" />
      <q:set name="home.crowd" value="{m.crowd}" />
      <q:set name="home.gate" value="{m.crowd * home.ticket}" />
      <q:set name="home.balance" value="{home.balance + home.gate}" />
      <q:set name="away.gate" value="{0}" />
      <q:set name="home.history" value="{([ {'vs': away.short, 'home': true, 'style': m.styles[0], 'gf': m.hg, 'ga': m.ag} ] + home.history)[0:5]}" />
      <q:set name="away.history" value="{([ {'vs': home.short, 'home': false, 'style': m.styles[1], 'gf': m.ag, 'ga': m.hg} ] + away.history)[0:5]}" />
    </q:loop>
    <q:loop var="i" from="0" to="{len(clubs) - 1}">
      <q:set name="c" value="{clubs[i]}" />
      <q:set name="pay" value="{0}" />
      <q:loop items="{c.players}" var="p">
        <q:set name="pay" value="{pay + p.salary}" />
        <q:set name="played" value="{p.xi != ''}" />
        <q:if condition="{p.injured > 0 and p.off != 'injured'}"><q:set name="p.injured" value="{p.injured - 1}" /></q:if>   <!-- hurt today: out from the next match -->
        <q:if condition="{p.suspended > 0}"><q:set name="p.suspended" value="{p.suspended - 1}" /></q:if>
        <q:if condition="{p.off == 'red'}"><q:set name="p.suspended" value="{1}" /></q:if>
        <q:if condition="{p.yellows >= 3}"><q:set name="p.suspended" value="{1}" /><q:set name="p.yellows" value="{0}" /></q:if>
        <q:if condition="{played}"><q:set name="p.played" value="{p.played + 1}" /></q:if>
        <q:set name="p.form" value="{max(30, min(100, p.form + 8 - (14 if played else 0)))}" />   <!-- a week: everyone recovers, who played tires -->
        <q:set name="p.xi" value="{p.start}" />   <!-- the eleven as it started: a manager's comes back to it -->
        <q:set name="p.bench" value="{p.sat}" />
        <q:set name="p.off" value="{''}" />
        <q:set name="p.booked" value="{false}" />
      </q:loop>
      <q:set name="c.wages" value="{pay / 4}" />                   <!-- a week of the month's wages -->
      <q:set name="c.balance" value="{c.balance - c.wages}" />
      <q:if condition="{matchday % 4 == 3}">                            <!-- the month's end: TV, sponsorship, costs, by division -->
        <q:set name="c.balance" value="{c.balance + tv_of(c) + sponsor_of(c, place_in(orders[c.div - 1], i)) - costs_of(c)}" />
      </q:if>
    </q:loop>
    <q:set name="last" value="{matches}" />
    <q:call function="papers" />
    <q:call function="boards" />
    <q:set name="matchday" value="{matchday + 1}" />
    <q:call function="prepare_round" />
  </q:function>

  <!-- every club ready for the next round: its tactics as they will start, its eleven (the gaps filled) -->
  <q:function name="prepare_round">
    <q:if condition="{matchday < 18}">
      <q:loop items="{fixtures[matchday]}" var="g">
        <q:call function="ready" args="{clubs[g[0]]}, {clubs[g[1]]}, {true}" />
        <q:call function="ready" args="{clubs[g[1]]}, {clubs[g[0]]}, {false}" />
      </q:loop>
    </q:if>
  </q:function>

  <q:function name="result" params="club, scored, conceded">
    <q:set name="club.played" value="{club.played + 1}" />
    <q:set name="club.gf" value="{club.gf + scored}" />
    <q:set name="club.ga" value="{club.ga + conceded}" />
    <q:set name="mark" value="{'W' if scored > conceded else ('D' if scored == conceded else 'L')}" />
    <q:if condition="{mark == 'W'}"><q:set name="club.won" value="{club.won + 1}" /><q:set name="club.points" value="{club.points + 3}" /></q:if>
    <q:if condition="{mark == 'D'}"><q:set name="club.drawn" value="{club.drawn + 1}" /><q:set name="club.points" value="{club.points + 1}" /></q:if>
    <q:if condition="{mark == 'L'}"><q:set name="club.lost" value="{club.lost + 1}" /></q:if>
    <q:set name="club.form" value="{(club.form + [mark])[max(0, len(club.form) - 4):]}" />
    <q:loop items="{club.players}" var="p">
      <!-- a good player left out is unhappy, unless he was tired or could not play -->
      <q:set name="p.morale" value="{max(20, min(100, p.morale + {'W': 6, 'D': 0, 'L': -6}[mark] + (-3 if p.xi == '' and p.strength > 35 and p.form >= 70 and available(p) else 0)))}" />
    </q:loop>
  </q:function>

  <!-- the papers: now and then a word on the hidden genius -->
  <q:function name="papers">
    <q:set name="gem" value="{null}" />
    <q:set name="home_of" value="{null}" />
    <q:loop items="{clubs}" var="c">
      <q:if condition="{c.div >= 3}">
        <q:loop items="{c.players}" var="p"><q:if condition="{p.genius}"><q:set name="gem" value="{p}" /><q:set name="home_of" value="{c}" /></q:if></q:loop>
      </q:if>
    </q:loop>
    <q:if condition="{gem != null and matchday == 2}"><q:call function="said" args="{'They say a phenomenon plays in the lower divisions...'}, {''}" /></q:if>
    <q:if condition="{gem != null and matchday == 6}"><q:call function="said" args="{ {'GK': 'Rumour: the hidden phenomenon would be a goalkeeper.', 'DF': 'Rumour: the hidden phenomenon would be a defender.', 'MF': 'Rumour: the hidden phenomenon would be a midfielder.', 'FW': 'Rumour: the hidden phenomenon would be a forward.'}[gem.pos] }, {''}" /></q:if>
    <q:if condition="{gem != null and matchday == 11}"><q:call function="said" args="{'Revealed: the phenomenon plays for'}, {home_of.name + '!'}" /></q:if>
  </q:function>

  <!-- the season's end: its champions into the honours, two up and two down between each two divisions, and a new
       season with the same squads, rested -->
  <q:function name="new_season">
    <q:set name="orders" value="{[table_order(1), table_order(2), table_order(3), table_order(4)]}" />
    <q:set name="top" value="{top_scorers(1, 0)}" />
    <q:set name="honours" value="{[ {'season': season, 'champions': [clubs[orders[0][0]].name, clubs[orders[1][0]].name, clubs[orders[2][0]].name, clubs[orders[3][0]].name], 'scorer': top[0].name + ' (' + top[0].club + ', ' + str(top[0].goals) + ')' if len(top) > 0 else '-'} ] + honours}" />
    <q:call function="season_verdicts" args="{orders}" />
    <q:set name="was" value="{[]}" />
    <q:loop items="{managers}" var="t"><q:set name="was" value="{was + [clubs[t.club].div]}" /></q:loop>
    <q:loop var="d" from="1" to="3">
      <q:loop items="{[orders[d - 1][8], orders[d - 1][9]]}" var="down"><q:set name="moved" value="{clubs[down]}" /><q:set name="moved.div" value="{d + 1}" /></q:loop>
      <q:loop items="{[orders[d][0], orders[d][1]]}" var="up"><q:set name="moved" value="{clubs[up]}" /><q:set name="moved.div" value="{d}" /></q:loop>
    </q:loop>
    <q:loop var="mi" from="0" to="{len(managers) - 1}">
      <q:set name="mine" value="{clubs[managers[mi].club]}" />
      <q:if condition="{mine.div < was[mi]}"><q:call function="said" args="{'Promoted to the'}, {div_name(mine.div) + ': ' + mine.name}" /></q:if>
      <q:if condition="{mine.div > was[mi]}"><q:call function="said" args="{'Relegated to the'}, {div_name(mine.div) + ': ' + mine.name}" /></q:if>
    </q:loop>
    <q:set name="season" value="{season + 1}" />
    <q:loop items="{clubs}" var="c">
      <q:loop items="{['points', 'played', 'won', 'drawn', 'lost', 'gf', 'ga']}" var="k"><q:set name="c" index="{k}" value="{0}" /></q:loop>
      <q:set name="c.form" value="{[]}" />
      <q:loop items="{c.players}" var="p"><q:set name="p.morale" value="{70}" /><q:set name="p.form" value="{100}" /><q:set name="p.goals" value="{0}" /><q:set name="p.yellows" value="{0}" /><q:set name="p.reds" value="{0}" /></q:loop>
    </q:loop>
    <q:call function="draw_offers" />
    <q:call function="make_fixtures" />
    <q:call function="set_expectations" />
    <q:set name="matchday" value="{0}" />
    <q:set name="champion" value="{-1}" />
    <q:call function="prepare_round" />
    <q:call function="said" args="{'The Panda League kicks off:'}, {str(season)}" />
  </q:function>

  <!-- ===== Screens ===== -->

  <!-- The title: a new game, one of the three saved, the options. -->
  <qg:scene name="title" width="640" height="400" background="#0000a8">
    <qg:hud x="160" y="60" box="frame" font="assets/DejaVuSansMono.ttf" size="16">
      <qg:text value="{'    ☻  P A N D A F O O T  ☻    '}" color="#ffff55" />
      <qg:text value="{'  one manager, one league, the ball  '}" color="#55ffff" />
    </qg:hud>
    <qg:menu x="200" y="170" font="assets/DejaVuSansMono.ttf" size="14" box="frame">
      <qg:button label="New game"><q:call function="reset_game" /><qg:goto-scene name="new-game" /></qg:button>
      <qg:button label="{tr('Continue') + ' 1'}" if="{has_save(1)}"><qg:continue slot="1" /></qg:button>
      <qg:button label="{tr('Continue') + ' 2'}" if="{has_save(2)}"><qg:continue slot="2" /></qg:button>
      <qg:button label="{tr('Continue') + ' 3'}" if="{has_save(3)}"><qg:continue slot="3" /></qg:button>
      <qg:button label="Options"><qg:goto-scene name="options" /></qg:button>
      <qg:button label="Quit" if="{can_quit()}"><qg:quit /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- A new game: the world's number, the save, the managers and their clubs. -->
  <qg:scene name="new-game" width="640" height="400" background="#0000a8">
    <q:set name="who" value="" type="string" />
    <q:set name="taken" value="[]" type="array" />
    <qg:hud x="16" y="12" font="assets/DejaVuSansMono.ttf" size="14">
      <qg:text value="{'NEW GAME'}" color="#ffff55" />
      <qg:text value="{tr('Managers:') + ' ' + str(len(managers)) + '/4'}" />
    </qg:hud>
    <qg:menu x="16" y="60" font="assets/DejaVuSansMono.ttf" size="13" box="frame">
      <qg:slider label="World no." bind="world" min="1" max="999" step="1" />
      <qg:slider label="Save in slot" bind="slot" min="1" max="3" step="1" />
      <qg:field bind="who" label="Manager's name:" max-length="14" />
    </qg:menu>
    <qg:hud x="16" y="190" font="assets/DejaVuSansMono.ttf" size="13" if="{len(managers) > 0}">
      <qg:table source="{managers}" as="t"><qg:column value="{'☻ ' + fit(t.name, 15) + club_names[t.club]}" width="34" color="#ffff55" /></qg:table>
    </qg:hud>
    <qg:hud x="340" y="60" font="assets/DejaVuSansMono.ttf" size="13">
      <qg:text value="{'Choose the manager\'s club:'}" color="#55ffff" />
      <qg:text value="{'(a small club of the 4th division)'}" color="#55ffff" />
    </qg:hud>
    <qg:menu x="340" y="100" source="{[30, 31, 32, 33, 34, 35, 36, 37, 38, 39]}" as="i" font="assets/DejaVuSansMono.ttf" size="13" box="frame">
      <qg:button label="{club_names[i]}" if="{not (i in taken)}">
        <q:if condition="{len(managers) < 4}">
          <q:set name="managers" value="{managers + [ {'name': who if who != '' else tr('Manager') + ' ' + str(len(managers) + 1), 'club': i, 'patience': 50, 'career': new_career(club_names[i])} ]}" />
          <q:set name="taken" value="{taken + [i]}" />
          <q:set name="who" value="" />
        </q:if>
      </qg:button>
    </qg:menu>
    <qg:menu x="16" y="330" font="assets/DejaVuSansMono.ttf" size="13">
      <qg:button label="Start the league" if="{len(managers) > 0}"><qg:goto-scene name="world" /></qg:button>
      <qg:button label="Back"><q:call function="reset_game" /><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- The world is made from its number: the same number, the same clubs and players. -->
  <qg:scene name="world" width="640" height="400" background="#0000a8" seed="{world}">
    <q:call function="new_world" />
    <qg:timer after="1"><qg:save scene="dashboard" slot="{slot}" /><qg:goto-scene name="dashboard" /></qg:timer>
  </qg:scene>

  <!-- ===== The dashboard: the club at a glance, its eleven in view, the next match and who it is against ===== -->
  <qg:scene name="dashboard" width="640" height="400" background="#0000a8" save="true">
    <q:set name="g" value="{next_match(managers[turn].club)}" />
    <q:set name="opp" value="{g[1] if g[0] == managers[turn].club else g[0]}" />
    <qg:hud x="6" y="4" box="frame" font="assets/DejaVuSansMono.ttf" size="12">
      <qg:text value="{'PANDAFOOT  ' + fit(my_club().name, 16) + fit(managers[turn].name, 16) + tr('Round') + ' ' + str(matchday + 1) + '/18  ' + str(season)}" color="#ffff55" />
      <qg:text value="{fit(tr('Balance:'), 9) + fit(money(my_club().balance), 14) + tr('Place:') + ' ' + str(position_of(managers[turn].club)) + 'º ' + div_name(my_club().div) + '   ' + tr('Form:') + ' ' + join(form_of(my_club()), ' ')}" />
      <qg:text value="{fit(tr('Morale:'), 9) + blocks(team_morale(my_club()), 10) + '    ' + tr('Ground:') + ' ' + thousands(my_club().capacity, '.') + ' ' + tr('seats') + '   ' + tr('Board:') + ' ' + blocks(managers[turn].patience, 8)}" />
    </qg:hud>
    <qg:hud x="6" y="86" box="frame" font="assets/DejaVuSansMono.ttf" size="10">
      <qg:text value="{tr('LINE-UP') + ' ' + my_club().formation + '  (' + str(len(eleven(my_club()))) + '/11)'}" color="#55ffff" />
      <qg:table source="{lineup_rows(my_club())[0:16]}" as="p">
        <qg:column label="Pos" value="{tr(p.xi) if p.xi != '' else tr('res')}" width="4" color="{'#ffffff' if p.xi != '' else '#aaaaaa'}" />
        <qg:column label="Name" value="{p.name}" width="15" color="{'#ff55ff' if p.genius else ('#ffffff' if p.xi != '' else '#aaaaaa')}" />
        <qg:column label="Str" value="{p.strength}" width="3" align="right" />
        <qg:column label="Form" value="{p.form}" width="5" align="right" color="{form_color(p)}" />
        <qg:column label="Fit" value="{state_of(p)}" width="3" color="{'#55ff55' if available(p) else '#ff5555'}" />
      </qg:table>
    </qg:hud>
    <qg:hud x="250" y="86" box="frame" font="assets/DejaVuSansMono.ttf" size="11">
      <qg:text value="{'═══ ' + tr('NEXT MATCH') + ' ═══'}" color="#55ffff" />
      <qg:text value="{fit(clubs[g[0]].name + '  x  ' + clubs[g[1]].name, 50)}" color="#ffffff" />
      <qg:text value="{fit(div_name(my_club().div) + ', ' + tr('round') + ' ' + str(matchday + 1) + '  (' + tr('home' if g[0] == managers[turn].club else 'away') + ')', 50)}" />
      <qg:text value="{fit(tr('Opponent:') + ' ' + str(position_of(opp)) + 'º   ' + tr('Form:') + ' ' + join(form_of(clubs[opp]), ' ') + '   ' + tr('Top scorer:') + ' ' + club_top(clubs[opp]), 50)}" />
      <qg:text value="{fit(tr('They tend to play:') + ' ' + tr(usual(clubs[opp])) + ' - ' + hint(my_club(), clubs[opp]), 50)}" />
      <qg:text value="{fit(tr('Objective:') + ' ' + objective_text(my_club()) + '   ' + my_club().formation + ' ' + tr(my_club().style), 50)}" color="#ffff55" />
      <qg:text value="{('⚠ ' + tr('The line-up is not complete (F1)')) if not lineup_ok(my_club()) else (('⚠ ' + tr('The board is losing its patience')) if managers[turn].patience < 20 else (tr('The board expects:') + ' ' + str(my_club().expect) + 'º'))}" color="{'#ff5555' if not lineup_ok(my_club()) or managers[turn].patience < 20 else '#aaaaaa'}" />
    </qg:hud>
    <qg:hud x="250" y="238" box="frame" font="assets/DejaVuSansMono.ttf" size="11">
      <qg:text value="{'═══ ' + tr('NEWS') + ' ═══'}" color="#55ffff" />
      <qg:table source="{news[0:5]}" as="n"><qg:column value="{tr(n.text) + (' ' + n.arg if n.arg != '' else '')}" width="50" /></qg:table>
    </qg:hud>
    <qg:hud x="8" y="356" font="assets/DejaVuSansMono.ttf" size="12">
      <qg:text value="{'[F1] ' + tr('Line-up') + ' [F2] ' + tr('Tactics') + ' [F3] ' + tr('Squad') + ' [F5] ' + tr('Finances') + ' [F7] ' + tr('Table')}" color="#55ffff" />
      <qg:text value="{'[ENTER] ' + tr('Ready: next manager' if turn < len(managers) - 1 else 'Play the round') + '   [ESC] ' + tr('Save and leave')}" color="#ffff55" />
    </qg:hud>
    <qg:on-input action="lineup"><qg:goto-scene name="lineup" /></qg:on-input>
    <qg:on-input action="tactics"><qg:goto-scene name="tactics" /></qg:on-input>
    <qg:on-input action="squad"><qg:goto-scene name="squad" /></qg:on-input>
    <qg:on-input action="finances"><qg:goto-scene name="finances" /></qg:on-input>
    <qg:on-input action="standings"><qg:goto-scene name="standings" /></qg:on-input>
    <qg:on-input action="select">
      <q:if condition="{not lineup_ok(my_club())}"><q:call function="fill_lineup" args="{my_club()}" /></q:if>
      <q:if condition="{turn < len(managers) - 1}">
        <q:set name="turn" value="{turn + 1}" />
        <qg:goto-scene name="dashboard" />
        <q:else>
          <q:set name="turn" value="{0}" />
          <qg:goto-scene name="round" />
        </q:else>
      </q:if>
    </qg:on-input>
    <qg:on-input action="cancel"><qg:save slot="{slot}" /><qg:goto-scene name="title" /></qg:on-input>
    <!-- the season is over: back from the table (F7 on the last results) or from a save, the season's end, never
         round 19 of 18 (it played the last match again, and again) -->
    <qg:when condition="{matchday >= 18}"><qg:goto-scene name="season-end" /></qg:when>
    <qg:when condition="{len(clubs) != 40}"><qg:goto-scene name="old-save" /></qg:when>
  </qg:scene>

  <!-- a save of the first PandaFoot (one league of ten): this one cannot continue it -->
  <qg:scene name="old-save" width="640" height="400" background="#0000a8">
    <qg:hud position="center" box="frame" font="assets/DejaVuSansMono.ttf" size="14">
      <qg:text value="{tr('This game was saved by the first PandaFoot')}" color="#ffff55" />
      <qg:text value="{tr('(one league of ten clubs), which this one')}" />
      <qg:text value="{tr('cannot continue. Start a new game: four')}" />
      <qg:text value="{tr('divisions, from a small club of the 4th.')}" />
      <qg:text value="{'[ENTER] ' + tr('To the title')}" color="#55ffff" />
    </qg:hud>
    <qg:on-input action="select"><q:call function="reset_game" /><qg:goto-scene name="title" /></qg:on-input>
  </qg:scene>

  <q:function name="next_match" params="club_index">
    <q:loop items="{fixtures[min(matchday, 17)]}" var="g">
      <q:if condition="{g[0] == club_index or g[1] == club_index}"><q:return value="{g}" /></q:if>
    </q:loop>
    <q:return value="{[club_index, club_index]}" />
  </q:function>

  <!-- the eleven by place, the keeper first, then the bench (the dashboard shows five of it) -->
  <q:function name="lineup_rows" params="club">
    <q:set name="out" value="{[]}" />
    <q:loop items="{['GK', 'DF', 'MF', 'FW']}" var="place">
      <q:loop items="{club.players}" var="p"><q:if condition="{p.xi == place}"><q:set name="out" value="{out + [p]}" /></q:if></q:loop>
    </q:loop>
    <q:loop items="{club.players}" var="p"><q:if condition="{p.xi == '' and p.bench}"><q:set name="out" value="{out + [p]}" /></q:if></q:loop>
    <q:return value="{out}" />
  </q:function>

  <!-- how fresh a player is, in colour: rested, tiring, tired -->
  <q:function name="form_color" params="p">
    <q:return value="{'#55ff55' if p.form >= 80 else ('#ffff55' if p.form >= 60 else '#ff5555')}" />
  </q:function>

  <!-- a manager's objective as the dashboard says it: Auto with what it picked for this match -->
  <q:function name="objective_text" params="club">
    <q:return value="{tr('Auto') + ' (' + tr(club.plan) + ')' if club.objective == 'Auto' else tr(club.objective)}" />
  </q:function>

  <!-- a club's best scorer of the season -->
  <q:function name="club_top" params="club">
    <q:set name="top" value="{null}" />
    <q:loop items="{club.players}" var="p"><q:if condition="{p.goals > 0 and (top == null or p.goals > top.goals)}"><q:set name="top" value="{p}" /></q:if></q:loop>
    <q:return value="{'-' if top == null else top.name + ' (' + str(top.goals) + ')'}" />
  </q:function>

  <!-- the last results, W D L, as the player's language writes them -->
  <q:function name="form_of" params="club">
    <q:set name="out" value="{[]}" />
    <q:loop items="{club.form}" var="f"><q:set name="out" value="{out + [tr(f)]}" /></q:loop>
    <q:return value="{out}" />
  </q:function>

  <q:function name="team_morale" params="club">
    <q:set name="sum" value="{0}" />
    <q:loop items="{club.players}" var="p"><q:set name="sum" value="{sum + p.morale}" /></q:loop>
    <q:return value="{sum / len(club.players)}" />
  </q:function>

  <!-- the traits as marks: the same in every language, the legend below says them -->
  <q:function name="marks" params="p">
    <q:set name="out" value="{'◆' if p.genius else ''}" />
    <q:loop items="{p.traits}" var="t">
      <q:set name="out" value="{out + {'Ace': '★', 'Finisher': '►', 'Set pieces': '◎', 'Leader': '♛', 'Star': '☆', 'Wall': '▣'}[t]}" />
    </q:loop>
    <q:return value="{out}" />
  </q:function>

  <q:function name="positions" params="p">
    <q:set name="out" value="{tr(p.pos)}" />
    <q:loop items="{p.sec}" var="s"><q:set name="out" value="{out + '/' + tr(s)}" /></q:loop>
    <q:return value="{out}" />
  </q:function>

  <q:function name="state_of" params="p">
    <q:return value="{('✚' + str(p.injured)) if p.injured > 0 else (('▮' + str(p.suspended)) if p.suspended > 0 else '✓')}" />
  </q:function>

  <!-- ===== F3: the squad ===== -->
  <qg:scene name="squad" width="640" height="400" background="#0000a8">
    <qg:hud x="8" y="6" box="frame" font="assets/DejaVuSansMono.ttf" size="11">
      <qg:text value="{tr('SQUAD') + ' - ' + shown_club().name + '   (' + str(position_of(shown_index())) + 'º, ' + str(len(shown_club().players)) + ' ' + tr('players, wages') + ' ' + money(payroll(shown_club())) + tr('/month') + ')'}" color="#ffff55" />
      <qg:table source="{shown_club().players}" as="p">
        <qg:column label="#" value="{p.num}" width="2" align="right" />
        <qg:column label="Name" value="{p.name}" width="17" />
        <qg:column label="Pos" value="{positions(p)}" width="11" />
        <qg:column label="Str" value="{p.strength}" width="3" align="right" color="{'#ff55ff' if known_genius(p) else ('#ffff55' if p.strength >= 42 else '#ffffff')}" />
        <qg:column label="Traits" value="{marks(p) if known_genius(p) or not p.genius else marks(p)[1:]}" width="6" color="#ff55ff" />
        <qg:column label="Morale" value="{blocks(p.morale, 5)}" width="6" color="{'#55ff55' if p.morale >= 70 else ('#ffff55' if p.morale >= 40 else '#ff5555')}" />
        <qg:column label="Form" value="{p.form}" width="5" align="right" color="{form_color(p)}" />
        <qg:column label="Goals" value="{p.goals}" width="5" align="right" />
        <qg:column label="▮" value="{p.yellows}" width="2" align="right" color="#ffff55" />
        <qg:column label="Fit" value="{state_of(p)}" width="3" color="{'#55ff55' if available(p) else '#ff5555'}" />
        <qg:column label="Salary" value="{money(p.salary)}" width="9" align="right" />
      </qg:table>
    </qg:hud>
    <qg:hud x="8" y="382" font="assets/DejaVuSansMono.ttf" size="11">
      <qg:text value="{'◆ ' + tr('Genius') + ' ★ ' + tr('Ace') + ' ► ' + tr('Finisher') + ' ◎ ' + tr('Set pieces') + ' ♛ ' + tr('Leader') + ' ☆ ' + tr('Star') + ' ▣ ' + tr('Wall') + '   [ESC] ' + tr('Back')}" color="#55ffff" />
    </qg:hud>
    <qg:on-input action="lineup"><q:set name="viewing" value="{-1}" /><qg:goto-scene name="lineup" /></qg:on-input>
    <qg:on-input action="tactics"><q:set name="viewing" value="{-1}" /><qg:goto-scene name="tactics" /></qg:on-input>
    <qg:on-input action="finances"><q:set name="viewing" value="{-1}" /><qg:goto-scene name="finances" /></qg:on-input>
    <qg:on-input action="standings"><q:set name="viewing" value="{-1}" /><qg:goto-scene name="standings" /></qg:on-input>
    <qg:on-input action="cancel">
      <q:if condition="{viewing >= 0}"><qg:goto-scene name="standings" />
        <q:else><qg:goto-scene name="dashboard" /></q:else>
      </q:if>
    </qg:on-input>
  </qg:scene>

  <!-- the squad on screen: the club chosen on the table, else the manager's -->
  <q:function name="shown_index">
    <q:return value="{viewing if viewing >= 0 else managers[turn].club}" />
  </q:function>

  <q:function name="shown_club">
    <q:return value="{clubs[shown_index()]}" />
  </q:function>

  <!-- a genius one knows of: the manager's own, and the big clubs' (the papers write about them); the one hidden in
       a small club is a rumour until someone finds him -->
  <q:function name="known_genius" params="p">
    <q:return value="{p.genius and (shown_index() == managers[turn].club or shown_club().div == 1)}" />
  </q:function>

  <q:function name="payroll" params="club">
    <q:set name="sum" value="{0}" />
    <q:loop items="{club.players}" var="p"><q:set name="sum" value="{sum + p.salary}" /></q:loop>
    <q:return value="{sum}" />
  </q:function>

  <!-- ===== F1: the line-up: choose a player to put them in the eleven, on the bench, or out ===== -->
  <qg:scene name="lineup" width="640" height="400" background="#0000a8">
    <qg:hud x="8" y="8" font="assets/DejaVuSansMono.ttf" size="12">
      <qg:text value="{tr('LINE-UP') + ' - ' + my_club().name + '   ' + my_club().formation + '   ' + tr('in the eleven:') + ' ' + str(len(eleven(my_club()))) + '/11'}" color="#ffff55" />
      <qg:text value="{'  #  ' + fit(tr('Name'), 18) + fit(tr('Pos'), 12) + fit(tr('Str'), 4) + fit(tr('Form'), 6) + fit(tr('Traits'), 7) + fit(tr('Fit'), 4) + tr('Plays')}" color="#55ffff" />
    </qg:hud>
    <qg:menu x="8" y="40" source="{my_club().players}" as="p" rows="18" font="assets/DejaVuSansMono.ttf" size="12">
      <qg:button label="{fit(p.num, 3, 'right') + '  ' + fit(p.name, 18) + fit(positions(p), 12) + fit(p.strength, 3, 'right') + ' ' + fit(p.form, 5, 'right') + ' ' + fit(marks(p), 7) + fit(state_of(p), 4) + (tr('ELEVEN') + ' ' + tr(p.xi) if p.xi != '' else (tr('bench') if p.bench else ''))}">
        <q:call function="toggle" args="{my_club()}, {p}" />
      </qg:button>
    </qg:menu>
    <qg:hud x="8" y="356" font="assets/DejaVuSansMono.ttf" size="12">
      <qg:text value="{tr('Attack') + ' ' + str(round(power(my_club())[0])) + '   ' + tr('Defence') + ' ' + str(round(power(my_club())[1])) + ('' if lineup_ok(my_club()) else '   ⚠ ' + tr('eleven fit to play, one of them in goal'))}" color="{'#ffffff' if lineup_ok(my_club()) else '#ff5555'}" />
      <qg:text value="{'[ENTER] ' + tr('Eleven → bench → out') + '   [A] ' + tr('Automatic') + '   [F2] ' + tr('Tactics') + '   [ESC] ' + tr('Back')}" color="#55ffff" />
    </qg:hud>
    <qg:on-input action="auto"><q:call function="auto_lineup" args="{my_club()}" /></qg:on-input>
    <qg:on-input action="tactics"><qg:goto-scene name="tactics" /></qg:on-input>
    <qg:on-input action="squad"><qg:goto-scene name="squad" /></qg:on-input>
    <qg:on-input action="cancel"><qg:goto-scene name="dashboard" /></qg:on-input>
  </qg:scene>

  <!-- a player chosen in the line-up: in the eleven, then on the bench, then out -->
  <q:function name="toggle" params="club, p">
    <q:if condition="{p.xi != ''}"><q:set name="p.xi" value="{''}" /><q:set name="p.bench" value="{true}" /><q:return /></q:if>
    <q:if condition="{p.bench}"><q:set name="p.bench" value="{false}" /><q:return /></q:if>
    <q:if condition="{available(p) and len(eleven(club)) < 11}"><q:set name="p.xi" value="{open_place(club, p)}" /></q:if>
  </q:function>

  <!-- where a player goes into the eleven: their own place if it is open, a second one, else any open -->
  <q:function name="open_place" params="club, p">
    <q:set name="n" value="{shape(club.formation)}" />
    <q:set name="wanted" value="{ {'GK': 1, 'DF': n[0], 'MF': n[1], 'FW': n[2]} }" />
    <q:loop items="{eleven(club)}" var="q"><q:set name="wanted" index="{q.xi}" value="{wanted[q.xi] - 1}" /></q:loop>
    <q:if condition="{wanted[p.pos] > 0}"><q:return value="{p.pos}" /></q:if>
    <q:loop items="{p.sec}" var="s"><q:if condition="{wanted[s] > 0}"><q:return value="{s}" /></q:if></q:loop>
    <q:loop items="{['DF', 'MF', 'FW', 'GK']}" var="s"><q:if condition="{wanted[s] > 0}"><q:return value="{s}" /></q:if></q:loop>
    <q:return value="{p.pos}" />
  </q:function>

  <!-- ===== F2: tactics: the objective, or the formation and the style by hand; the opponent's last matches ===== -->
  <qg:scene name="tactics" width="640" height="400" background="#0000a8">
    <q:set name="g" value="{next_match(managers[turn].club)}" />
    <q:set name="opponent" value="{clubs[g[1] if g[0] == managers[turn].club else g[0]]}" />
    <qg:hud x="8" y="8" box="frame" font="assets/DejaVuSansMono.ttf" size="13">
      <qg:text value="{tr('TACTICS') + ' - ' + my_club().name + ' x ' + opponent.name}" color="#ffff55" />
      <qg:text value="{tr('They tend to play:') + ' ' + tr(usual(opponent)) + '   ' + hint(my_club(), opponent)}" color="#55ffff" />
    </qg:hud>
    <qg:menu x="8" y="82" font="assets/DejaVuSansMono.ttf" size="13" box="frame">
      <qg:button label="{tr('Objective:') + ' ' + objective_text(my_club())}"><q:call function="next_objective" args="{my_club()}, {opponent}, {g[0] == managers[turn].club}" /></qg:button>
      <qg:button label="{tr('Formation:') + ' ' + my_club().formation}"><q:call function="by_hand" args="{my_club()}, {after_in(formations, my_club().formation)}, {my_club().style}" /></qg:button>
      <qg:button label="{tr('Style:') + ' ' + tr(my_club().style)}"><q:call function="by_hand" args="{my_club()}, {my_club().formation}, {after_in(styles, my_club().style)}" /></qg:button>
      <qg:button label="Back"><qg:goto-scene name="dashboard" /></qg:button>
    </qg:menu>
    <qg:hud x="300" y="82" box="frame" font="assets/DejaVuSansMono.ttf" size="11">
      <qg:text value="{'═══ ' + tr('AUTOMATIC CHANGES') + ' ═══'}" color="#55ffff" />
      <qg:table source="{my_club().reactions}" as="r">
        <qg:column label="When" value="{tr(r.when)}" width="10" />
        <qg:column label="after" value="{str(r.after) + '′'}" width="6" align="right" />
        <qg:column label="change to" value="{r.formation + ' ' + tr(r.style)}" width="22" />
      </qg:table>
    </qg:hud>
    <qg:hud x="8" y="222" box="frame" font="assets/DejaVuSansMono.ttf" size="12">
      <qg:text value="{'═══ ' + opponent.name + ' - ' + tr('LAST MATCHES') + ' ═══'}" color="#55ffff" />
      <qg:table source="{opponent.history}" as="h">
        <qg:column value="{tr('vs') + ' ' + h.vs + ' (' + tr('home' if h.home else 'away') + ')'}" width="22" />
        <qg:column value="{tr(h.style)}" width="17" />
        <qg:column value="{str(h.gf) + '-' + str(h.ga) + '  ' + tr('W' if h.gf > h.ga else ('D' if h.gf == h.ga else 'L'))}" width="8" color="{'#55ff55' if h.gf > h.ga else ('#ffffff' if h.gf == h.ga else '#ff5555')}" />
      </qg:table>
      <qg:text value="{tendency(opponent)}" color="#ffff55" />
    </qg:hud>
    <qg:on-input action="lineup"><qg:goto-scene name="lineup" /></qg:on-input>
    <qg:on-input action="cancel"><qg:goto-scene name="dashboard" /></qg:on-input>
  </qg:scene>

  <!-- the formation or the style by hand: the objective is the manager's own -->
  <q:function name="by_hand" params="club, formation, style">
    <q:set name="club.formation" value="{formation}" />
    <q:set name="club.style" value="{style}" />
    <q:set name="club.objective" value="{'By hand'}" />
    <q:set name="club.plan" value="{'By hand'}" />
    <q:set name="club.reactions" value="{[]}" />
    <q:call function="fill_lineup" args="{club}" />
  </q:function>

  <q:function name="ticket" params="club, by">
    <q:set name="club.ticket" value="{max(5, min(50, club.ticket + by))}" />
  </q:function>

  <!-- the next objective: its tactics against this opponent at once -->
  <q:function name="next_objective" params="club, opponent, home">
    <q:set name="club.objective" value="{after_in(objectives, club.objective)}" />
    <q:if condition="{club.objective == 'By hand'}"><q:call function="preset" args="{club}, {'By hand'}, {usual(opponent)}" /><q:set name="club.plan" value="{'By hand'}" /></q:if>
    <q:call function="ready" args="{club}, {opponent}, {home}" />
  </q:function>

  <!-- what the counter-tactics give against the opponent's usual style -->
  <q:function name="hint" params="club, opponent">
    <q:set name="e" value="{edge(club.style, usual(opponent))}" />
    <q:if condition="{e > 0}"><q:return value="{tr('Tactical edge') + ' +' + str(round(e * 100)) + '%'}" /></q:if>
    <q:if condition="{e < 0}"><q:return value="{tr('Tactical handicap') + ' ' + str(round(e * 100)) + '%'}" /></q:if>
    <q:return value="{tr('No tactical edge')}" />
  </q:function>

  <!-- what a club started its last matches with, and the style that beats it -->
  <q:function name="tendency" params="club">
    <q:if condition="{len(club.history) == 0}"><q:return value="{tr('No matches yet.')}" /></q:if>
    <q:set name="theirs" value="{usual(club)}" />
    <q:set name="share" value="{0}" />
    <q:loop items="{club.history}" var="h"><q:if condition="{family(h.style) == family(theirs)}"><q:set name="share" value="{share + 1}" /></q:if></q:loop>
    <q:set name="beat" value="{ {'A': 'Counter-attack', 'D': 'Attacking', 'C': 'Defensive', 'B': 'Attacking'}[family(theirs)] }" />
    <q:return value="{tr('Tendency:') + ' ' + tr(theirs) + ' (' + str(share) + '/' + str(len(club.history)) + ')   ' + tr('Against it:') + ' ' + tr(beat) + ' +' + str(round(edge(beat, theirs) * 100)) + '%'}" />
  </q:function>

  <!-- ===== F7: the table, and the top scorers ===== -->
  <qg:scene name="standings" width="640" height="400" background="#0000a8">
    <!-- the division shown: the club's just looked at, else the manager's; Tab, the next -->
    <q:set name="shown" value="{clubs[viewing].div if viewing >= 0 else my_club().div}" type="number" />
    <qg:hud x="8" y="4" box="frame" font="assets/DejaVuSansMono.ttf" size="13">
      <qg:text value="{tr('PANDA LEAGUE') + ' ' + str(season) + ' - ' + div_name(shown) + ' - ' + tr('Round') + ' ' + str(matchday) + '/18'}" color="#ffff55" />
    </qg:hud>
    <qg:hud x="26" y="40" font="assets/DejaVuSansMono.ttf" size="13">
      <qg:text value="{fit(tr('Pos'), 4, 'right') + '  ' + fit(tr('Club'), 14) + fit(tr('P'), 3, 'right') + fit(tr('W'), 3, 'right') + fit(tr('D'), 3, 'right') + fit(tr('L'), 3, 'right') + fit(tr('GF'), 4, 'right') + fit(tr('GA'), 4, 'right') + fit(tr('GD'), 4, 'right') + fit(tr('Pts'), 5, 'right') + '  ' + tr('Form')}" color="#55ffff" />
    </qg:hud>
    <!-- a club's row, chosen with Enter: its squad (the managers' clubs are marked ►) -->
    <qg:menu x="8" y="58" source="{table_order(shown)}" as="i" font="assets/DejaVuSansMono.ttf" size="13" box="frame">
      <qg:button label="{table_row(i)}"><q:set name="viewing" value="{i}" /><qg:goto-scene name="squad" /></qg:button>
    </qg:menu>
    <qg:hud x="468" y="58" box="frame" font="assets/DejaVuSansMono.ttf" size="10">
      <qg:text value="{'═ ' + tr('TOP SCORERS') + ' ═'}" color="#55ffff" />
      <qg:table source="{top_scorers(10, shown)}" as="t">
        <qg:column value="{t.goals}" width="3" align="right" color="#ffff55" />
        <qg:column value="{t.name}" width="14" color="{'#ff55ff' if t.genius else '#ffffff'}" />
        <qg:column value="{t.club}" width="4" />
      </qg:table>
    </qg:hud>
    <qg:hud x="8" y="364" font="assets/DejaVuSansMono.ttf" size="13">
      <qg:text value="{'► ' + tr('managers') + '  ↑↓ ' + tr('up and down') + '  [ENTER] ' + tr('Squad') + '  [TAB] ' + tr('Division') + '  [ESC] ' + tr('Back')}" color="#55ffff" />
    </qg:hud>
    <qg:on-input action="other"><q:set name="shown" value="{shown % 4 + 1}" /></qg:on-input>
    <qg:on-input action="cancel"><qg:goto-scene name="dashboard" /></qg:on-input>
    <qg:on-input action="squad"><qg:goto-scene name="squad" /></qg:on-input>
    <qg:when condition="{viewing >= 0}"><q:set name="viewing" value="{-1}" /></qg:when>   <!-- back from a club's squad -->
  </qg:scene>

  <q:function name="table_row" params="i">
    <q:set name="c" value="{clubs[i]}" />
    <q:set name="at" value="{position_of(i)}" />
    <q:return value="{fit(str(at) + '.', 4, 'right') + ('↑' if c.div > 1 and at <= 2 else ('↓' if c.div < 4 and at >= 9 else ' ')) + ('►' if c.manager > 0 else ' ') + fit(c.name, 14) + fit(str(c.played), 3, 'right') + fit(str(c.won), 3, 'right') + fit(str(c.drawn), 3, 'right') + fit(str(c.lost), 3, 'right') + fit(str(c.gf), 4, 'right') + fit(str(c.ga), 4, 'right') + fit(str(c.gf - c.ga), 4, 'right') + fit(str(c.points), 5, 'right') + '  ' + join(form_of(c), ' ')}" />
  </q:function>

  <!-- the season's top scorers of a division (0: of all four), so many of them: the goals, then the order of the
       clubs and squads -->
  <q:function name="top_scorers" params="n, d">
    <q:set name="keys" value="{[]}" />
    <q:loop var="ci" from="0" to="{len(clubs) - 1}">
      <q:if condition="{d == 0 or clubs[ci].div == d}">
        <q:loop var="pk" from="0" to="{len(clubs[ci].players) - 1}">
          <q:if condition="{clubs[ci].players[pk].goals > 0}"><q:set name="keys" value="{keys + [[clubs[ci].players[pk].goals, 100000 - ci * 100 - pk]]}" /></q:if>
        </q:loop>
      </q:if>
    </q:loop>
    <q:set name="out" value="{[]}" />
    <q:loop items="{sort(keys, true)[0:n]}" var="key">
      <q:set name="at" value="{int(100000 - key[1])}" />
      <q:set name="his" value="{clubs[int(floor(at / 100))]}" />
      <q:set name="who" value="{his.players[at % 100]}" />
      <q:set name="out" value="{out + [ {'name': who.name, 'goals': who.goals, 'genius': who.genius, 'club': his.short} ]}" />
    </q:loop>
    <q:return value="{out}" />
  </q:function>

  <!-- ===== F5: finances ===== -->
  <qg:scene name="finances" width="640" height="400" background="#0000a8">
    <q:set name="g" value="{next_match(managers[turn].club)}" />
    <q:set name="opp" value="{g[1] if g[0] == managers[turn].club else g[0]}" />
    <qg:hud x="8" y="8" box="frame" font="assets/DejaVuSansMono.ttf" size="13">
      <qg:text value="{tr('FINANCES') + ' - ' + my_club().name}" color="#ffff55" />
      <qg:text value="{fit(tr('Balance:'), 26) + fit(money(my_club().balance), 14, 'right')}" color="{'#55ff55' if my_club().balance >= 0 else '#ff5555'}" />
      <qg:text value="{fit(tr('Wages a month:'), 26) + fit(money(payroll(my_club())), 14, 'right')}" />
      <qg:text value="{fit(tr('Wages a week:'), 26) + fit(money(payroll(my_club()) / 4), 14, 'right')}" />
      <qg:text value="{fit(tr('Last gate:'), 26) + fit(money(my_club().gate), 14, 'right')}" />
      <qg:text value="{fit(tr('Last crowd:'), 26) + fit(thousands(my_club().crowd, '.'), 14, 'right')}" />
      <qg:text value="{fit(tr('TV a month:'), 26) + fit(money(tv_of(my_club())), 14, 'right')}" />
      <qg:text value="{fit(tr('Sponsor a month:'), 26) + fit(money(sponsor_of(my_club(), position_of(managers[turn].club) - 1)), 14, 'right')}" />
      <qg:text value="{fit(tr('Costs a month:'), 26) + fit(money(costs_of(my_club())), 14, 'right')}" />
      <qg:text value="{fit(tr('Ground:'), 26) + fit(thousands(my_club().capacity, '.') + ' ' + tr('seats'), 14, 'right')}" />
      <qg:text value="{fit(tr('Ticket:'), 26) + fit(money(my_club().ticket), 14, 'right')}" color="#ffff55" />
      <qg:text value="{fit(tr('Crowd at this price:'), 26) + fit(thousands(crowd_for(my_club(), position_of(opp) - 1, position_of(managers[turn].club) - 1, 0.85), '.') + '-' + thousands(crowd_for(my_club(), position_of(opp) - 1, position_of(managers[turn].club) - 1, 1.15), '.'), 14, 'right')}" color="#ffff55" />
    </qg:hud>
    <qg:hud x="200" y="296" font="assets/DejaVuSansMono.ttf" size="12">
      <qg:text value="{tr('A dearer ticket keeps people away:')}" color="#55ffff" />
      <qg:text value="{tr('a full ground lifts the side')}" color="#55ffff" />
      <qg:text value="{tr('(up to a quarter more at home).')}" color="#55ffff" />
    </qg:hud>
    <qg:menu x="8" y="290" font="assets/DejaVuSansMono.ttf" size="13">
      <qg:button label="{tr('Ticket') + ' +$1'}"><q:call function="ticket" args="{my_club()}, {1}" /></qg:button>
      <qg:button label="{tr('Ticket') + ' -$1'}"><q:call function="ticket" args="{my_club()}, {-1}" /></qg:button>
      <qg:button label="Back"><qg:goto-scene name="dashboard" /></qg:button>
    </qg:menu>
    <qg:on-input action="cancel"><qg:goto-scene name="dashboard" /></qg:on-input>
  </qg:scene>

  <!-- ===== The live round: every match of it in the same minute ===== -->
  <!-- seeded by the world, the season and the round: the same game from the same world, and each round its own luck -->
  <qg:scene name="round" width="640" height="400" background="#0000a8" seed="{world * 1000 + (season - 2026) * 18 + matchday}">
    <q:set name="minute" value="0" type="number" />
    <q:set name="clock" value="0" type="number" />        <!-- ticks towards the next minute -->
    <q:set name="pace" value="2" type="number" />         <!-- 1x 2x 4x 8x 16x -->
    <q:set name="flash" value="0" type="number" />
    <q:set name="stopped" value="false" type="boolean" />
    <q:set name="timeouts" value="[3, 3, 3, 3]" type="array" />
    <q:set name="pending" value="[]" type="array" />      <!-- a manager's automatic change, three seconds to undo it: [match, side, reaction, formation, style before] -->
    <q:set name="subbing" value="false" type="boolean" /> <!-- in a pause, F1: a substitution being chosen -->
    <q:set name="leaving" value="-1" type="number" />     <!-- who comes off: an index of the squad, -1 not chosen yet -->
    <q:set name="scored" value="0" type="number" />
    <q:set name="live" value="{kickoff()}" type="array" />    <!-- the round's matches, as they go -->
    <q:set name="before" value="{table_order(clubs[managers[0].club].div)}" type="array" />    <!-- the first manager's division's table as the round starts -->
    <q:set name="focus" value="{match_of(managers[0].club)}" type="number" />    <!-- the match in front -->
    <qg:timer after="1"><qg:play sound="whistle" /></qg:timer>

    <!-- a minute every 30 ticks at 1x: the match in 45 seconds; 16x in under three -->
    <qg:timer every="1">
      <q:if condition="{not stopped and minute < 90}">
        <q:set name="clock" value="{clock + pace}" />
        <q:loop var="k" from="1" to="{floor(clock / 30)}">
          <q:if condition="{minute < 90}">
            <q:set name="minute" value="{minute + 1}" />
            <q:loop items="{live}" var="m">
              <q:set name="scored" value="{play_minute(m, minute)}" />
              <q:if condition="{scored > 0}"><q:set name="flash" value="{90}" /><qg:play sound="goal" /></q:if>
            </q:loop>
            <q:call function="reactions" />
          </q:if>
        </q:loop>
        <q:set name="clock" value="{clock % 30}" />
        <q:if condition="{minute >= 90}">
          <qg:play sound="final" />
          <qg:after seconds="2"><q:call function="finish_round" args="{live}" /><qg:goto-scene name="results" /></qg:after>
        </q:if>
      </q:if>
      <q:if condition="{flash > 0}"><q:set name="flash" value="{flash - 1}" /></q:if>
    </qg:timer>

    <qg:hud x="8" y="8" box="frame" font="assets/DejaVuSansMono.ttf" size="14" if="{len(live) > 0}">
      <qg:text value="{clubs[live[focus].home].name + '  ' + str(live[focus].hg) + ' x ' + str(live[focus].ag) + '  ' + clubs[live[focus].away].name}" color="#ffff55" />
      <qg:text value="{'[' + repeat('█', floor(minute / 4.5)) + repeat('░', 20 - floor(minute / 4.5)) + '] ' + str(minute) + '′ - ' + tr('first half' if minute <= 45 else 'second half') + '   ' + str(pace) + 'x   ' + tr('Crowd:') + ' ' + thousands(live[focus].crowd, '.')}" />
      <qg:text value="{stats_line(live[focus])}" color="#55ffff" />
    </qg:hud>
    <qg:hud x="8" y="100" box="frame" font="assets/DejaVuSansMono.ttf" size="13" if="{len(live) > 0 and not subbing}">
      <qg:table source="{live[focus].events[0:8]}" as="e">
        <qg:column value="{event_text(e)}" width="44" color="{event_color(e)}" />
      </qg:table>
    </qg:hud>
    <qg:hud x="400" y="100" box="frame" font="assets/DejaVuSansMono.ttf" size="13" if="{len(live) > 0}">
      <qg:text value="{'═══ ' + tr('LIVE ROUND') + ' ═══'}" color="#55ffff" />
      <qg:text value="{div_name(clubs[live[focus].home].div)}" color="#55ffff" />
      <qg:table source="{matches_of(clubs[live[focus].home].div)}" as="m">
        <qg:column value="{clubs[m.home].short}" width="4" color="{'#ffff55' if clubs[m.home].manager > 0 else '#ffffff'}" />
        <qg:column value="{str(m.hg) + ' x ' + str(m.ag)}" width="6" align="right" />
        <qg:column value="{' ' + clubs[m.away].short}" width="5" color="{'#ffff55' if clubs[m.away].manager > 0 else '#ffffff'}" />
        <qg:column value="{tr('GOAL') + '!' if len(m.events) > 0 and m.events[0].kind == 'goal' and flash > 0 else ''}" width="5" color="#ffff55" />
      </qg:table>
      <qg:text value="{live_move()}" color="#55ff55" />
    </qg:hud>
    <!-- the substitution, in a pause: who comes off, then who comes on -->
    <qg:hud x="8" y="100" font="assets/DejaVuSansMono.ttf" size="12" if="{subbing}">
      <qg:text value="{tr('Who comes off?') if leaving < 0 else tr('Who comes on for') + ' ' + me_in_focus().players[leaving].name + '?'}" color="#ffff55" />
    </qg:hud>
    <qg:menu x="8" y="120" source="{pitch_of_me()}" as="k" if="{subbing and leaving < 0}" font="assets/DejaVuSansMono.ttf" size="12" box="frame">
      <qg:button label="{sub_label(k)}"><q:set name="leaving" value="{k}" /></qg:button>
    </qg:menu>
    <qg:menu x="8" y="120" source="{bench_of_me()}" as="k" if="{subbing and leaving >= 0}" font="assets/DejaVuSansMono.ttf" size="12" box="frame">
      <qg:button label="{sub_label(k)}"><q:call function="substitute" args="{k}" /></qg:button>
    </qg:menu>
    <qg:hud position="center" size="40" font="assets/DejaVuSansMono.ttf" if="{flash > 60 and ticks() % 20 < 12}">
      <qg:text value="{tr('GOOOOOAL!')}" color="#ffff55" />
    </qg:hud>
    <qg:hud x="8" y="264" box="frame" font="assets/DejaVuSansMono.ttf" size="13" if="{len(pending) > 0 and not subbing}">
      <qg:text value="{'⚙ ' + tr('AUTOMATIC CHANGE') + ' - ' + pending_text()}" color="#ffff55" />
      <qg:text value="{'[C] ' + tr('Undo') + '   [ENTER] ' + tr('Keep') + '   (' + tr('three seconds to undo it') + ')'}" color="#55ffff" />
    </qg:hud>
    <qg:hud x="8" y="340" font="assets/DejaVuSansMono.ttf" size="13" if="{len(live) > 0}">
      <qg:text value="{('■ ' + tr('PAUSED') + ' - ' if stopped else '') + '[' + tr('SPACE') + '] ' + (tr('Go on') if stopped else ((tr('Time-out') + ' (' + str(timeouts[turn_of_focus()]) + ')') if len(managers) > 1 and turn_of_focus() >= 0 else tr('Pause'))) + '  [+/-] ' + tr('Speed') + '  [TAB] ' + tr('Another match')}" color="#55ffff" />
      <qg:text value="{('[F1] ' + tr('Substitution') + ' (' + str(subs_of_me()) + '/3)   [F2] ' + tr('Tactics of') + ' ' + me_in_focus().name) if stopped and me_in_focus() != null else ''}" color="#ffff55" />
    </qg:hud>

    <qg:on-input action="faster"><q:set name="pace" value="{min(16, pace * 2)}" /></qg:on-input>
    <qg:on-input action="slower"><q:set name="pace" value="{max(1, pace / 2)}" /></qg:on-input>
    <qg:on-input action="other"><q:if condition="{not subbing}"><q:set name="focus" value="{(focus + 1) % len(live)}" /></q:if></qg:on-input>
    <qg:on-input action="pause">
      <q:if condition="{stopped}"><q:set name="stopped" value="{false}" /><q:set name="subbing" value="{false}" /><q:set name="leaving" value="{-1}" />
        <q:elseif condition="{len(managers) == 1}"><q:set name="stopped" value="{true}" /></q:elseif>
        <q:elseif condition="{turn_of_focus() >= 0 and timeouts[turn_of_focus()] > 0}">
          <q:set name="timeouts" index="{turn_of_focus()}" value="{timeouts[turn_of_focus()] - 1}" />
          <q:set name="stopped" value="{true}" />
          <qg:after seconds="30" name="timeout"><q:set name="stopped" value="{false}" /><q:set name="subbing" value="{false}" /><q:set name="leaving" value="{-1}" /></qg:after>
        </q:elseif>
      </q:if>
    </qg:on-input>
    <qg:on-input action="lineup"><q:if condition="{stopped and me_in_focus() != null and subs_of_me() < 3}"><q:set name="subbing" value="{true}" /><q:set name="leaving" value="{-1}" /></q:if></qg:on-input>
    <qg:on-input action="cancel"><q:set name="subbing" value="{false}" /><q:set name="leaving" value="{-1}" /></qg:on-input>
    <qg:on-input action="tactics"><q:if condition="{stopped and me_in_focus() != null and not subbing}"><q:call function="next_style" /></q:if></qg:on-input>
    <qg:on-input action="undo"><q:if condition="{len(pending) > 0}"><q:call function="undo_pending" /></q:if></qg:on-input>
    <qg:on-input action="select"><q:set name="pending" value="{[]}" /></qg:on-input>

    <!-- the reactions due this minute, at once: a manager's with three seconds to undo it -->
    <q:function name="reactions">
      <q:loop var="j" from="0" to="{len(live) - 1}">
        <q:set name="m" value="{live[j]}" />
        <q:loop items="{['h', 'a']}" var="s">
          <q:set name="k" value="{due(m, s, minute)}" />
          <q:if condition="{k >= 0}">
            <q:set name="done" value="{m[s].done + [k]}" />
            <q:set name="m_side" value="{m[s]}" />
            <q:set name="m_side.done" value="{done}" />
            <q:set name="club" value="{clubs[m.home if s == 'h' else m.away]}" />
            <q:if condition="{club.manager > 0}">
              <q:set name="pending" value="{[j, s, k, club.formation, club.style]}" />
              <qg:after seconds="3" name="reaction"><q:set name="pending" value="{[]}" /></qg:after>
            </q:if>
            <q:call function="change" args="{m}, {s}, {club.reactions[k].formation}, {club.reactions[k].style}" />
          </q:if>
        </q:loop>
      </q:loop>
    </q:function>
    <!-- the manager's side of the match in front: 'h' or 'a' -->
    <q:function name="my_side">
      <q:return value="{'h' if live[focus].home == managers[turn_of_focus()].club else 'a'}" />
    </q:function>
    <!-- in a pause, F2: the next style for the manager's side of the match in front -->
    <q:function name="next_style">
      <q:call function="change" args="{live[focus]}, {my_side()}, {me_in_focus().formation}, {after_in(styles, me_in_focus().style)}" />
    </q:function>
    <!-- the substitutions made by the manager's side of the match in front -->
    <q:function name="subs_of_me">
      <q:if condition="{me_in_focus() == null}"><q:return value="{0}" /></q:if>
      <q:return value="{live[focus][my_side()].subs}" />
    </q:function>
    <!-- who of the manager's club is on the pitch, and who on the bench may come on: indices of the squad -->
    <q:function name="pitch_of_me">
      <q:set name="out" value="{[]}" />
      <q:if condition="{me_in_focus() == null}"><q:return value="{out}" /></q:if>
      <q:set name="squad" value="{me_in_focus().players}" />
      <q:loop var="k" from="0" to="{len(squad) - 1}"><q:if condition="{squad[k].xi != '' and squad[k].off == ''}"><q:set name="out" value="{out + [k]}" /></q:if></q:loop>
      <q:return value="{out}" />
    </q:function>
    <q:function name="bench_of_me">
      <q:set name="out" value="{[]}" />
      <q:if condition="{me_in_focus() == null}"><q:return value="{out}" /></q:if>
      <q:set name="squad" value="{me_in_focus().players}" />
      <q:loop var="k" from="0" to="{len(squad) - 1}"><q:if condition="{squad[k].bench and squad[k].xi == '' and squad[k].off == '' and available(squad[k])}"><q:set name="out" value="{out + [k]}" /></q:if></q:loop>
      <q:return value="{out}" />
    </q:function>
    <q:function name="sub_label" params="k">
      <q:set name="p" value="{me_in_focus().players[k]}" />
      <q:return value="{fit(tr(p.xi) if p.xi != '' else tr(p.pos), 4) + fit(p.name, 17) + fit(p.strength, 3, 'right') + '  ' + tr('Form') + ' ' + fit(p.form, 3, 'right') + ('  ▮' if p.booked else '')}" />
    </q:function>
    <!-- F1, then the two choices: the substitution made, the side as it stands now -->
    <q:function name="substitute" params="k">
      <q:set name="m" value="{live[focus]}" />
      <q:set name="s" value="{my_side()}" />
      <q:if condition="{m[s].subs < 3}">
        <q:call function="bring_on" args="{m}, {s}, {me_in_focus().players[leaving]}, {me_in_focus().players[k]}, {minute}" />
        <q:call function="refresh" args="{m}, {s}" />
      </q:if>
      <q:set name="subbing" value="{false}" />
      <q:set name="leaving" value="{-1}" />
    </q:function>
    <!-- C: the automatic change undone, the tactics as they were -->
    <q:function name="undo_pending">
      <q:call function="change" args="{live[pending[0]]}, {pending[1]}, {pending[3]}, {pending[4]}" />
      <q:set name="pending" value="{[]}" />
    </q:function>
    <q:function name="pending_text">
      <q:set name="m" value="{live[pending[0]]}" />
      <q:set name="club" value="{clubs[m.home if pending[1] == 'h' else m.away]}" />
      <q:set name="r" value="{club.reactions[pending[2]]}" />
      <q:return value="{club.short + ' ' + tr(r.when) + ', ' + str(r.after) + '′: ' + r.formation + ' ' + tr(r.style)}" />
    </q:function>
    <q:function name="match_of" params="club_index">
      <q:loop var="k" from="0" to="{len(live) - 1}">
        <q:if condition="{live[k].home == club_index or live[k].away == club_index}"><q:return value="{k}" /></q:if>
      </q:loop>
      <q:return value="{0}" />
    </q:function>
    <!-- the manager whose club plays the match in front (-1: none) -->
    <q:function name="turn_of_focus">
      <q:loop var="k" from="0" to="{len(managers) - 1}">
        <q:if condition="{live[focus].home == managers[k].club or live[focus].away == managers[k].club}"><q:return value="{k}" /></q:if>
      </q:loop>
      <q:return value="{-1}" />
    </q:function>
    <q:function name="me_in_focus">
      <q:if condition="{turn_of_focus() >= 0}"><q:return value="{clubs[managers[turn_of_focus()].club]}" /></q:if>
      <q:return value="{null}" />
    </q:function>
    <!-- the round's matches of a division, as they go -->
    <q:function name="matches_of" params="d">
      <q:set name="out" value="{[]}" />
      <q:loop items="{live}" var="m"><q:if condition="{clubs[m.home].div == d}"><q:set name="out" value="{out + [m]}" /></q:if></q:loop>
      <q:return value="{out}" />
    </q:function>
    <!-- the table as it would be now: the first manager's club, where it was and where it is -->
    <q:function name="live_move">
      <q:set name="keys" value="{[]}" />
      <q:loop items="{in_div(clubs[managers[0].club].div)}" var="i">
        <q:set name="c" value="{clubs[i]}" />
        <q:set name="pts" value="{c.points}" />
        <q:set name="gd" value="{c.gf - c.ga}" />
        <q:loop items="{live}" var="m">
          <q:if condition="{m.home == i}"><q:set name="pts" value="{pts + (3 if m.hg > m.ag else (1 if m.hg == m.ag else 0))}" /><q:set name="gd" value="{gd + m.hg - m.ag}" /></q:if>
          <q:if condition="{m.away == i}"><q:set name="pts" value="{pts + (3 if m.ag > m.hg else (1 if m.hg == m.ag else 0))}" /><q:set name="gd" value="{gd + m.ag - m.hg}" /></q:if>
        </q:loop>
        <q:set name="keys" value="{keys + [[pts, gd, 1000 - i]]}" />
      </q:loop>
      <q:set name="now" value="{[]}" />
      <q:loop items="{sort(keys, true)}" var="k"><q:set name="now" value="{now + [1000 - k[2]]}" /></q:loop>
      <q:set name="mine" value="{managers[0].club}" />
      <q:set name="was_at" value="{place_in(before, mine) + 1}" />
      <q:set name="now_at" value="{place_in(now, mine) + 1}" />
      <q:return value="{clubs[mine].short + ': ' + tr('place') + ' ' + str(was_at) + ' → ' + str(now_at) + ' ' + ('↑' if now_at < was_at else ('↓' if now_at > was_at else '='))}" />
    </q:function>
  </qg:scene>

  <!-- ===== After the round: the results with their scorers, the manager's match, the purses ===== -->
  <qg:scene name="results" width="640" height="400" background="#0000a8">
    <q:set name="shown" value="{clubs[managers[0].club].div}" type="number" />
    <qg:hud x="8" y="6" box="frame" font="assets/DejaVuSansMono.ttf" size="11">
      <qg:text value="{'✓ ' + tr('ROUND') + ' ' + str(matchday) + ' ' + tr('PLAYED') + ' - ' + div_name(shown)}" color="#ffff55" />
      <qg:table source="{last_of(shown)}" as="m">
        <qg:column value="{clubs[m.home].name}" width="13" align="right" color="{'#ffff55' if clubs[m.home].manager > 0 else '#ffffff'}" />
        <qg:column value="{str(m.hg) + ' x ' + str(m.ag)}" width="7" align="right" />
        <qg:column value="{' ' + clubs[m.away].name}" width="14" color="{'#ffff55' if clubs[m.away].manager > 0 else '#ffffff'}" />
        <qg:column value="{scorers_line(m)}" width="42" color="#aaaaaa" />
      </qg:table>
    </qg:hud>
    <qg:hud x="8" y="126" box="frame" font="assets/DejaVuSansMono.ttf" size="12" if="{my_last() != null}">
      <qg:text value="{'═══ ' + tr('YOUR MATCH') + ' ═══  ' + clubs[my_last().home].name + ' ' + str(my_last().hg) + ' x ' + str(my_last().ag) + ' ' + clubs[my_last().away].name}" color="#55ffff" />
      <qg:text value="{tr('Crowd:') + ' ' + thousands(my_last().crowd, '.') + ' (' + str(round(my_last().fill * 100)) + '%)   ' + tr('Gate:') + ' ' + money(my_last().crowd * clubs[my_last().home].ticket) + ' (' + clubs[my_last().home].short + ')'}" />
      <qg:text value="{fit(tr('Man of the match:') + ' ' + man_of_match(my_last()), 52) + '  ' + shots_line(my_last())}" color="#ffff55" />
      <qg:text value="{fit(tr('Booked:') + ' ' + names_of(my_last(), 'card') + '   ' + tr('Sent off:') + ' ' + names_of(my_last(), 'red'), 84)}" />
      <qg:text value="{fit(tr('Injured:') + ' ' + names_of(my_last(), 'knock') + '   ' + tr('Came on:') + ' ' + names_of(my_last(), 'sub'), 84)}" />
      <qg:text value="{fit(tr('Out of the next match:') + ' ' + out_next(clubs[managers[0].club]), 84)}" color="#ff5555" />
    </qg:hud>
    <qg:hud x="8" y="256" box="frame" font="assets/DejaVuSansMono.ttf" size="12">
      <qg:text value="{'═══ ' + tr('THE MANAGERS') + ' ═══'}" color="#55ffff" />
      <qg:table source="{managers}" as="t">
        <qg:column value="{t.name}" width="14" />
        <qg:column value="{clubs[t.club].name}" width="16" />
        <qg:column value="{str(position_of(t.club)) + '.'}" width="5" align="right" />
        <qg:column value="{'+' + money(clubs[t.club].gate) if clubs[t.club].gate > 0 else ''}" width="13" align="right" color="#55ff55" />
        <qg:column value="{'-' + money(clubs[t.club].wages)}" width="12" align="right" color="#ff5555" />
        <qg:column value="{money(clubs[t.club].balance)}" width="14" align="right" color="{'#55ff55' if clubs[t.club].balance >= 0 else '#ff5555'}" />
      </qg:table>
    </qg:hud>
    <qg:hud x="8" y="364" font="assets/DejaVuSansMono.ttf" size="13">
      <qg:text value="{'[ENTER] ' + tr('End of the season' if matchday >= 18 else 'Next round') + '   [F7] ' + tr('Table') + '   [TAB] ' + tr('Another division')}" color="#55ffff" />
    </qg:hud>
    <qg:on-input action="other"><q:set name="shown" value="{shown % 4 + 1}" /></qg:on-input>
    <qg:on-input action="standings"><qg:goto-scene name="standings" /></qg:on-input>
    <qg:hud x="8" y="318" box="frame" font="assets/DejaVuSansMono.ttf" size="12" if="{len(jobs) > 0 and jobs[0].kind == 'sacked'}">
      <qg:text value="{'✖ ' + tr('SACKED') + ': ' + managers[jobs[0].who].name}" color="#ff5555" />
    </qg:hud>
    <qg:on-input action="select">
      <q:if condition="{len(jobs) > 0}"><qg:goto-scene name="job" />
        <q:elseif condition="{matchday >= 18}"><qg:goto-scene name="season-end" /></q:elseif>
        <q:else><qg:goto-scene name="dashboard" /></q:else>
      </q:if>
    </qg:on-input>
  </qg:scene>

  <!-- the last round's matches of a division -->
  <q:function name="last_of" params="d">
    <q:set name="out" value="{[]}" />
    <q:loop items="{last}" var="m"><q:if condition="{clubs[m.home].div == d}"><q:set name="out" value="{out + [m]}" /></q:if></q:loop>
    <q:return value="{out}" />
  </q:function>

  <!-- a match's scorers, the home side's and the away side's: Silva 12', Souza 70' / Lima 33' -->
  <q:function name="scorers_line" params="m">
    <q:set name="mine" value="{[]}" />
    <q:set name="theirs" value="{[]}" />
    <q:loop items="{m.events}" var="e">
      <q:if condition="{e.kind == 'goal' and e.club == clubs[m.home].short}"><q:set name="mine" value="{[e.who + ' ' + str(e.minute) + '′'] + mine}" /></q:if>
      <q:if condition="{e.kind == 'goal' and e.club == clubs[m.away].short}"><q:set name="theirs" value="{[e.who + ' ' + str(e.minute) + '′'] + theirs}" /></q:if>
    </q:loop>
    <q:if condition="{len(mine) + len(theirs) == 0}"><q:return value="{''}" /></q:if>
    <q:return value="{join(mine, ', ') + ' / ' + join(theirs, ', ')}" />
  </q:function>

  <!-- the first manager's match of the last round (null: none) -->
  <q:function name="my_last">
    <q:loop items="{last}" var="m"><q:if condition="{m.home == managers[0].club or m.away == managers[0].club}"><q:return value="{m}" /></q:if></q:loop>
    <q:return value="{null}" />
  </q:function>

  <!-- the man of the match: who scored most in it (a winner's scorer before a loser's) -->
  <q:function name="man_of_match" params="m">
    <q:set name="names" value="{[]}" />
    <q:loop items="{m.events}" var="e"><q:if condition="{e.kind == 'goal'}"><q:set name="names" value="{names + [e.who + ' (' + e.club + ')']}" /></q:if></q:loop>
    <q:if condition="{len(names) == 0}"><q:return value="{tr('the keepers')}" /></q:if>
    <q:set name="best" value="{names[len(names) - 1]}" />
    <q:loop items="{names}" var="who"><q:if condition="{times_in(names, who) > times_in(names, best)}"><q:set name="best" value="{who}" /></q:if></q:loop>
    <q:return value="{best + ', ' + str(times_in(names, best)) + ' ' + tr('goals' if times_in(names, best) > 1 else 'goal')}" />
  </q:function>

  <!-- the first manager's players in a match's events of a kind: the booked, the sent off, the injured, who came on -->
  <q:function name="names_of" params="m, kind">
    <q:set name="short" value="{clubs[managers[0].club].short}" />
    <q:set name="out" value="{[]}" />
    <q:loop items="{m.events}" var="e"><q:if condition="{e.kind == kind and e.club == short}"><q:set name="out" value="{[e.who] + out}" /></q:if></q:loop>
    <q:return value="{'-' if len(out) == 0 else join(out, ', ')}" />
  </q:function>

  <!-- who cannot play the next match, and why: ▮ suspended, ✚ injured (for so many matches) -->
  <q:function name="out_next" params="club">
    <q:set name="out" value="{[]}" />
    <q:loop items="{club.players}" var="p">
      <q:if condition="{p.suspended > 0}"><q:set name="out" value="{out + [p.name + ' ▮']}" /></q:if>
      <q:if condition="{p.injured > 0}"><q:set name="out" value="{out + [p.name + ' ✚' + str(p.injured)]}" /></q:if>
    </q:loop>
    <q:return value="{'-' if len(out) == 0 else join(out, ', ')}" />
  </q:function>

  <!-- ===== The season's end ===== -->
  <qg:scene name="season-end" width="640" height="400" background="#0000a8">
    <qg:hud x="8" y="8" box="frame" font="assets/DejaVuSansMono.ttf" size="15">
      <qg:text value="{'♛ ' + tr('CHAMPIONS') + ' ' + str(season) + ' ♛'}" color="#ffff55" />
      <qg:text value="{fit(div_name(1) + ':', 16) + clubs[table_order(1)[0]].name + '  ' + manager_of(table_order(1)[0])}" color="#ffffff" />
      <qg:text value="{fit(div_name(2) + ':', 16) + clubs[table_order(2)[0]].name + '  ' + manager_of(table_order(2)[0])}" color="#ffffff" />
      <qg:text value="{fit(div_name(3) + ':', 16) + clubs[table_order(3)[0]].name + '  ' + manager_of(table_order(3)[0])}" color="#ffffff" />
      <qg:text value="{fit(div_name(4) + ':', 16) + clubs[table_order(4)[0]].name + '  ' + manager_of(table_order(4)[0])}" color="#ffffff" />
      <qg:text value="{tr('Top scorer:') + ' ' + (top_scorers(1, 0)[0].name + ' (' + top_scorers(1, 0)[0].club + ', ' + str(top_scorers(1, 0)[0].goals) + ')' if len(top_scorers(1, 0)) > 0 else '-')}" color="#55ffff" />
    </qg:hud>
    <qg:hud x="8" y="190" box="frame" font="assets/DejaVuSansMono.ttf" size="13">
      <qg:text value="{'═══ ' + tr('UP AND DOWN') + ' ═══'}" color="#55ffff" />
      <qg:text value="{'↑ ' + tr('to the') + ' ' + div_name(1) + ': ' + clubs[table_order(2)[0]].name + ', ' + clubs[table_order(2)[1]].name + '   ↓ ' + clubs[table_order(1)[8]].name + ', ' + clubs[table_order(1)[9]].name}" />
      <qg:text value="{'↑ ' + tr('to the') + ' ' + div_name(2) + ': ' + clubs[table_order(3)[0]].name + ', ' + clubs[table_order(3)[1]].name + '   ↓ ' + clubs[table_order(2)[8]].name + ', ' + clubs[table_order(2)[9]].name}" />
      <qg:text value="{'↑ ' + tr('to the') + ' ' + div_name(3) + ': ' + clubs[table_order(4)[0]].name + ', ' + clubs[table_order(4)[1]].name + '   ↓ ' + clubs[table_order(3)[8]].name + ', ' + clubs[table_order(3)[9]].name}" />
      <qg:text value="{fate(managers[0].club)}" color="#ffff55" />
    </qg:hud>
    <qg:menu position="bottom-center" font="assets/DejaVuSansMono.ttf" size="14">
      <qg:button label="New season"><q:call function="new_season" /><q:if condition="{len(jobs) > 0}"><qg:goto-scene name="job" /><q:else><qg:goto-scene name="dashboard" /></q:else></q:if></qg:button>
      <qg:button label="To the title"><qg:save slot="{slot}" /><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- what waits for a manager: sacked, the clubs that would have them (or the end of the career); or a bigger
       club's offer (or staying) -->
  <qg:scene name="job" width="640" height="400" background="#0000a8">
    <q:set name="j" value="{jobs[0]}" />
    <q:set name="t" value="{managers[j.who]}" />
    <qg:hud x="16" y="16" box="frame" font="assets/DejaVuSansMono.ttf" size="15">
      <qg:text value="{('✖ ' + tr('SACKED')) if j.kind == 'sacked' else ('✉ ' + tr('AN OFFER'))}" color="{'#ff5555' if j.kind == 'sacked' else '#ffff55'}" />
      <qg:text value="{t.name + ', ' + clubs[t.club].name}" color="#ffffff" />
      <qg:text value="{tr('The board has lost its patience.') if j.kind == 'sacked' else tr('Your work has been noticed.')}" />
      <qg:text value="{(tr('These clubs would have you:') if len(j.clubs) > 0 else tr('No club would have you now.')) if j.kind == 'sacked' else tr('These clubs would have you:')}" color="#55ffff" />
    </qg:hud>
    <qg:menu x="16" y="170" source="{j.clubs}" as="ci" font="assets/DejaVuSansMono.ttf" size="14" box="frame">
      <qg:button label="{tr('Take') + ' ' + clubs[ci].name + ' (' + div_name(clubs[ci].div) + ', ' + tr('expects') + ' ' + str(clubs[ci].expect) + 'º)'}">
        <q:call function="take_job" args="{j.who}, {ci}" /><q:call function="next_job" args="{true}" />
      </qg:button>
    </qg:menu>
    <qg:menu x="16" y="300" font="assets/DejaVuSansMono.ttf" size="14">
      <qg:button label="{tr('Stay at') + ' ' + clubs[t.club].name}" if="{j.kind == 'offer'}"><q:call function="next_job" args="{true}" /></qg:button>
      <qg:button label="End the career" if="{j.kind == 'sacked'}"><q:call function="end_career" args="{j.who}" /><q:call function="next_job" args="{false}" /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- the job dealt with (`done`: still the first of the list; a career ended took its jobs with it): the next one, or
       the game goes on (or ends, with no manager left) -->
  <q:function name="next_job" params="done">
    <q:if condition="{done and len(jobs) > 0}"><q:set name="jobs" value="{jobs[1:]}" /></q:if>
    <q:if condition="{len(managers) == 0}"><qg:goto-scene name="career-over" />
      <q:elseif condition="{len(jobs) > 0}"><qg:goto-scene name="job" /></q:elseif>
      <q:elseif condition="{matchday >= 18}"><qg:goto-scene name="season-end" /></q:elseif>
      <q:else><qg:goto-scene name="dashboard" /></q:else>
    </q:if>
  </q:function>

  <!-- no manager left: the careers, and to the title -->
  <qg:scene name="career-over" width="640" height="400" background="#0000a8">
    <qg:hud position="center" box="frame" font="assets/DejaVuSansMono.ttf" size="14">
      <qg:text value="{'═══ ' + tr('THE END OF THE CAREER') + ' ═══'}" color="#ffff55" />
      <qg:table source="{retired}" as="r">
        <qg:column value="{r.name}" width="14" />
        <qg:column value="{str(r.career.seasons) + ' ' + tr('seasons') + ', ' + str(r.career.titles) + ' ' + tr('titles') + ', ' + str(r.career.ups) + ' ↑'}" width="30" />
        <qg:column value="{join(r.career.clubs, ', ')}" width="30" color="#aaaaaa" />
      </qg:table>
      <qg:text value="{'[ENTER] ' + tr('To the title')}" color="#55ffff" />
    </qg:hud>
    <qg:on-input action="select"><q:call function="reset_game" /><qg:goto-scene name="title" /></qg:on-input>
  </qg:scene>

  <!-- a club's season in a line: its place, and up, down or staying -->
  <q:function name="fate" params="club_index">
    <q:set name="c" value="{clubs[club_index]}" />
    <q:set name="at" value="{position_of(club_index)}" />
    <q:set name="move" value="{tr('promoted!') if c.div > 1 and at <= 2 else (tr('relegated.') if c.div < 4 and at >= 9 else tr('stays in the') + ' ' + div_name(c.div) + '.')}" />
    <q:return value="{c.name + ': ' + str(at) + 'º ' + tr('of the') + ' ' + div_name(c.div) + ', ' + move}" />
  </q:function>

  <q:function name="manager_of" params="club_index">
    <q:loop items="{managers}" var="t"><q:if condition="{t.club == club_index}"><q:return value="{tr('Manager:') + ' ' + t.name}" /></q:if></q:loop>
    <q:return value="{''}" />
  </q:function>

  <!-- ===== Options ===== -->
  <qg:scene name="options" width="640" height="400" background="#0000a8">
    <qg:menu position="center" font="assets/DejaVuSansMono.ttf" size="14" box="frame">
      <qg:slider label="Sounds" bus="effects" />
      <qg:button label="{tr('Language') + ': ' + language()}"><qg:next-language /></qg:button>
      <qg:button label="{tr('Full screen') + ': ' + tr('yes' if fullscreen() else 'no')}"><qg:fullscreen /></qg:button>
      <qg:button label="Back"><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- ===== Portuguese and Spanish ===== -->
  <qg:language lang="pt" name="Português">
    <qg:phrase text="    ☻  P A N D A F O O T  ☻    " as="    ☻  P A N D A F O O T  ☻    " />
    <qg:phrase text="  one manager, one league, the ball  " as="  um técnico, uma liga, a bola  " />
    <qg:phrase text="New game" as="Novo jogo" />
    <qg:phrase text="Continue" as="Continuar" />
    <qg:phrase text="Options" as="Opções" />
    <qg:phrase text="Quit" as="Sair" />
    <qg:phrase text="NEW GAME" as="NOVO JOGO" />
    <qg:phrase text="Managers:" as="Técnicos:" />
    <qg:phrase text="World no." as="Mundo nº" />
    <qg:phrase text="Save in slot" as="Salvar no jogo" />
    <qg:phrase text="Manager's name:" as="Nome do técnico:" />
    <qg:phrase text="Choose the manager's club:" as="Escolha o clube do técnico:" />
    <qg:phrase text="big" as="grande" />
    <qg:phrase text="middle" as="médio" />
    <qg:phrase text="small" as="pequeno" />
    <qg:phrase text="Manager" as="Técnico" />
    <qg:phrase text="Start the league" as="Começar o campeonato" />
    <qg:phrase text="Back" as="Voltar" />
    <qg:phrase text="Round" as="Rodada" />
    <qg:phrase text="Balance:" as="Saldo:" />
    <qg:phrase text="Place:" as="Posição:" />
    <qg:phrase text="place" as="posição" />
    <qg:phrase text="Form:" as="Forma:" />
    <qg:phrase text="Morale:" as="Moral:" />
    <qg:phrase text="Ground:" as="Estádio:" />
    <qg:phrase text="seats" as="lugares" />
    <qg:phrase text="NEXT MATCH" as="PRÓXIMO JOGO" />
    <qg:phrase text="Panda League, round" as="Campeonato Panda, rodada" />
    <qg:phrase text="home" as="em casa" />
    <qg:phrase text="away" as="fora" />
    <qg:phrase text="Objective:" as="Objetivo:" />
    <qg:phrase text="The line-up is not complete (F1)" as="A escalação não está completa (F1)" />
    <qg:phrase text="NEWS" as="NOTÍCIAS" />
    <qg:phrase text="Line-up" as="Escalação" />
    <qg:phrase text="Tactics" as="Táticas" />
    <qg:phrase text="Squad" as="Elenco" />
    <qg:phrase text="Finances" as="Finanças" />
    <qg:phrase text="Table" as="Classificação" />
    <qg:phrase text="Ready: next manager" as="Pronto: próximo técnico" />
    <qg:phrase text="Play the round" as="Jogar a rodada" />
    <qg:phrase text="Save and leave" as="Salvar e sair" />
    <qg:phrase text="The Panda League kicks off:" as="Começa o Campeonato Panda:" />
    <qg:phrase text="They say a phenomenon plays in the lower divisions..." as="Dizem que um fenômeno joga nas divisões de baixo..." />
    <qg:phrase text="Rumour: the hidden phenomenon would be a goalkeeper." as="Boato: o fenômeno escondido seria um goleiro." />
    <qg:phrase text="Rumour: the hidden phenomenon would be a defender." as="Boato: o fenômeno escondido seria um defensor." />
    <qg:phrase text="Rumour: the hidden phenomenon would be a midfielder." as="Boato: o fenômeno escondido seria um meia." />
    <qg:phrase text="Rumour: the hidden phenomenon would be a forward." as="Boato: o fenômeno escondido seria um atacante." />
    <qg:phrase text="Revealed: the phenomenon plays for" as="Revelado: o fenômeno joga no" />
    <qg:phrase text="W" as="V" />
    <qg:phrase text="D" as="E" />
    <qg:phrase text="L" as="D" />
    <qg:phrase text="GK" as="GOL" />
    <qg:phrase text="DF" as="DEF" />
    <qg:phrase text="MF" as="MEI" />
    <qg:phrase text="FW" as="ATA" />
    <qg:phrase text="SQUAD" as="ELENCO" />
    <qg:phrase text="players, wages" as="jogadores, folha" />
    <qg:phrase text="/month" as="/mês" />
    <qg:phrase text="Name" as="Nome" />
    <qg:phrase text="Pos" as="Pos" />
    <qg:phrase text="Str" as="For" />
    <qg:phrase text="Traits" as="DNA" />
    <qg:phrase text="Morale" as="Moral" />
    <qg:phrase text="Form" as="Forma" />
    <qg:phrase text="Goals" as="Gols" />
    <qg:phrase text="Fit" as="Est" />
    <qg:phrase text="Salary" as="Salário" />
    <qg:phrase text="Genius" as="Gênio" />
    <qg:phrase text="Ace" as="Craque" />
    <qg:phrase text="Finisher" as="Finalizador" />
    <qg:phrase text="Set pieces" as="Cobrador" />
    <qg:phrase text="Leader" as="Líder" />
    <qg:phrase text="Star" as="Estrela" />
    <qg:phrase text="Wall" as="Muralha" />
    <qg:phrase text="LINE-UP" as="ESCALAÇÃO" />
    <qg:phrase text="in the eleven:" as="titulares:" />
    <qg:phrase text="Plays" as="No time" />
    <qg:phrase text="ELEVEN" as="TITULAR" />
    <qg:phrase text="bench" as="banco" />
    <qg:phrase text="Attack" as="Ataque" />
    <qg:phrase text="Defence" as="Defesa" />
    <qg:phrase text="eleven fit to play, one of them in goal" as="11 titulares em condições, um deles no gol" />
    <qg:phrase text="Eleven → bench → out" as="Titular → banco → fora" />
    <qg:phrase text="Automatic" as="Automática" />
    <qg:phrase text="TACTICS" as="TÁTICAS" />
    <qg:phrase text="They tend to play:" as="Costuma jogar:" />
    <qg:phrase text="Formation:" as="Formação:" />
    <qg:phrase text="Style:" as="Estilo:" />
    <qg:phrase text="AUTOMATIC CHANGES" as="REAÇÕES AUTOMÁTICAS" />
    <qg:phrase text="When" as="Se" />
    <qg:phrase text="after" as="após" />
    <qg:phrase text="change to" as="muda para" />
    <qg:phrase text="winning" as="ganhando" />
    <qg:phrase text="drawing" as="empatando" />
    <qg:phrase text="losing" as="perdendo" />
    <qg:phrase text="Balanced" as="Equilibrado" />
    <qg:phrase text="Attacking" as="Ofensivo" />
    <qg:phrase text="All-out attack" as="Muito ofensivo" />
    <qg:phrase text="Defensive" as="Defensivo" />
    <qg:phrase text="Park the bus" as="Muito defensivo" />
    <qg:phrase text="Counter-attack" as="Contra-ataque" />
    <qg:phrase text="Kamikaze" as="Kamikaze" />
    <qg:phrase text="Win" as="Vitória" />
    <qg:phrase text="Draw" as="Empate" />
    <qg:phrase text="Avoid defeat" as="Não perder" />
    <qg:phrase text="By hand" as="Decidir no jogo" />
    <qg:phrase text="Auto" as="Auto" />
    <qg:phrase text="Tactical edge" as="Vantagem tática" />
    <qg:phrase text="Tactical handicap" as="Desvantagem tática" />
    <qg:phrase text="No tactical edge" as="Sem vantagem tática" />
    <qg:phrase text="PANDA LEAGUE" as="CAMPEONATO PANDA" />
    <qg:phrase text="Club" as="Time" />
    <qg:phrase text="P" as="J" />
    <qg:phrase text="GF" as="GM" />
    <qg:phrase text="GA" as="GS" />
    <qg:phrase text="GD" as="SG" />
    <qg:phrase text="Pts" as="Pts" />
    <qg:phrase text="FINANCES" as="FINANÇAS" />
    <qg:phrase text="Wages a month:" as="Folha salarial/mês:" />
    <qg:phrase text="Wages a week:" as="Folha da semana:" />
    <qg:phrase text="Last gate:" as="Última bilheteria:" />
    <qg:phrase text="TV a month:" as="Cota de TV/mês:" />
    <qg:phrase text="Costs a month:" as="Custos/mês:" />
    <qg:phrase text="Ticket:" as="Ingresso:" />
    <qg:phrase text="Ticket" as="Ingresso" />
    <qg:phrase text="first half" as="1º tempo" />
    <qg:phrase text="second half" as="2º tempo" />
    <qg:phrase text="GOAL" as="GOL" />
    <qg:phrase text="injured" as="lesionado" />
    <qg:phrase text="LIVE ROUND" as="RODADA AO VIVO" />
    <qg:phrase text="GOOOOOAL!" as="GOOOOOL!" />
    <qg:phrase text="AUTOMATIC CHANGE" as="MUDANÇA TÁTICA AUTOMÁTICA" />
    <qg:phrase text="Undo" as="Desfazer" />
    <qg:phrase text="Keep" as="Manter" />
    <qg:phrase text="three seconds to undo it" as="3 segundos para desfazer" />
    <qg:phrase text="PAUSED" as="PAUSA" />
    <qg:phrase text="SPACE" as="ESPAÇO" />
    <qg:phrase text="Go on" as="Continuar" />
    <qg:phrase text="Time-out" as="Pedir tempo" />
    <qg:phrase text="Pause" as="Pausar" />
    <qg:phrase text="Speed" as="Velocidade" />
    <qg:phrase text="Another match" as="Outro jogo" />
    <qg:phrase text="Tactics of" as="Táticas do" />
    <qg:phrase text="ROUND" as="RODADA" />
    <qg:phrase text="PLAYED" as="FINALIZADA" />
    <qg:phrase text="THE MANAGERS" as="OS TÉCNICOS" />
    <qg:phrase text="End of the season" as="Fim de temporada" />
    <qg:phrase text="Next round" as="Próxima rodada" />
    <qg:phrase text="CHAMPIONS" as="CAMPEÕES" />
    <qg:phrase text="New season" as="Nova temporada" />
    <qg:phrase text="To the title" as="Ao título" />
    <qg:phrase text="Manager:" as="Técnico:" />
    <qg:phrase text="Sounds" as="Sons" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="Full screen" as="Tela cheia" />
    <qg:phrase text="yes" as="sim" />
    <qg:phrase text="no" as="não" />
    <qg:phrase text="(up to a quarter more at home)." as="(até um quarto a mais em casa)." />
    <qg:phrase text="A dearer ticket keeps people away:" as="Ingresso mais caro afasta o público;" />
    <qg:phrase text="a full ground lifts the side" as="estádio cheio empurra o time" />
    <qg:phrase text="Against it:" as="Contra isso:" />
    <qg:phrase text="Booked:" as="Amarelos:" />
    <qg:phrase text="Came on:" as="Entraram:" />
    <qg:phrase text="Crowd at this price:" as="Público com este ingresso:" />
    <qg:phrase text="Crowd:" as="Público:" />
    <qg:phrase text="Shots" as="Chutes" />
    <qg:phrase text="Ball" as="Posse" />
    <qg:phrase text="Pressing:" as="Pressão:" />
    <qg:phrase text="Gate:" as="Renda:" />
    <qg:phrase text="Injured:" as="Lesionados:" />
    <qg:phrase text="LAST MATCHES" as="ÚLTIMOS JOGOS" />
    <qg:phrase text="Last crowd:" as="Último público:" />
    <qg:phrase text="Man of the match:" as="Destaque:" />
    <qg:phrase text="No matches yet." as="Ainda sem jogos." />
    <qg:phrase text="Opponent:" as="Adversário:" />
    <qg:phrase text="Out of the next match:" as="Fora do próximo jogo:" />
    <qg:phrase text="Sent off:" as="Expulsos:" />
    <qg:phrase text="Substitution" as="Substituição" />
    <qg:phrase text="TOP SCORERS" as="ARTILHARIA" />
    <qg:phrase text="Tendency:" as="Tendência:" />
    <qg:phrase text="Top scorer:" as="Artilheiro:" />
    <qg:phrase text="Who comes off?" as="Quem sai?" />
    <qg:phrase text="Who comes on for" as="Quem entra no lugar de" />
    <qg:phrase text="YOUR MATCH" as="SEU JOGO" />
    <qg:phrase text="for" as="no lugar de" />
    <qg:phrase text="goal" as="gol" />
    <qg:phrase text="goals" as="gols" />
    <qg:phrase text="res" as="res" />
    <qg:phrase text="sent off" as="expulso" />
    <qg:phrase text="the keepers" as="os goleiros" />
    <qg:phrase text="vs" as="x" />
    <qg:phrase text="1st division" as="1ª divisão" />
    <qg:phrase text="2nd division" as="2ª divisão" />
    <qg:phrase text="3rd division" as="3ª divisão" />
    <qg:phrase text="4th division" as="4ª divisão" />
    <qg:phrase text="round" as="rodada" />
    <qg:phrase text="Sponsor a month:" as="Patrocínio por mês:" />
    <qg:phrase text="(a small club of the 4th division)" as="(um time pequeno da 4ª divisão)" />
    <qg:phrase text="up and down" as="sobe e desce" />
    <qg:phrase text="Another division" as="Outra divisão" />
    <qg:phrase text="Promoted to the" as="Subiu para a" />
    <qg:phrase text="Relegated to the" as="Caiu para a" />
    <qg:phrase text="UP AND DOWN" as="SOBE E DESCE" />
    <qg:phrase text="to the" as="para a" />
    <qg:phrase text="promoted!" as="subiu!" />
    <qg:phrase text="relegated." as="caiu." />
    <qg:phrase text="stays in the" as="fica na" />
    <qg:phrase text="of the" as="da" />
    <qg:phrase text="This game was saved by the first PandaFoot" as="Este jogo foi salvo pelo primeiro PandaFoot" />
    <qg:phrase text="(one league of ten clubs), which this one" as="(uma liga de dez times), que este não" />
    <qg:phrase text="cannot continue. Start a new game: four" as="consegue continuar. Comece um jogo novo: quatro" />
    <qg:phrase text="divisions, from a small club of the 4th." as="divisões, de um time pequeno da 4ª." />
    <qg:phrase text="managers" as="técnicos" />
    <qg:phrase text="Division" as="Divisão" />
    <qg:phrase text="Board:" as="Diretoria:" />
    <qg:phrase text="The board is losing its patience" as="A diretoria está perdendo a paciência" />
    <qg:phrase text="The board expects:" as="A diretoria espera:" />
    <qg:phrase text="Sacked by the board of" as="Demitido pela diretoria do" />
    <qg:phrase text="New manager of" as="Novo técnico do" />
    <qg:phrase text="SACKED" as="DEMITIDO" />
    <qg:phrase text="AN OFFER" as="UMA PROPOSTA" />
    <qg:phrase text="The board has lost its patience." as="A diretoria perdeu a paciência." />
    <qg:phrase text="Your work has been noticed." as="O seu trabalho chamou a atenção." />
    <qg:phrase text="These clubs would have you:" as="Estes clubes querem você:" />
    <qg:phrase text="No club would have you now." as="Nenhum clube quer você agora." />
    <qg:phrase text="Take" as="Assumir o" />
    <qg:phrase text="expects" as="espera" />
    <qg:phrase text="Stay at" as="Ficar no" />
    <qg:phrase text="End the career" as="Encerrar a carreira" />
    <qg:phrase text="THE END OF THE CAREER" as="FIM DA CARREIRA" />
    <qg:phrase text="seasons" as="temporadas" />
    <qg:phrase text="titles" as="títulos" />
  </qg:language>
  <qg:language lang="es" name="Español">
    <qg:phrase text="    ☻  P A N D A F O O T  ☻    " as="    ☻  P A N D A F O O T  ☻    " />
    <qg:phrase text="  one manager, one league, the ball  " as="  un técnico, una liga, la pelota  " />
    <qg:phrase text="New game" as="Nueva partida" />
    <qg:phrase text="Continue" as="Continuar" />
    <qg:phrase text="Options" as="Opciones" />
    <qg:phrase text="Quit" as="Salir" />
    <qg:phrase text="NEW GAME" as="NUEVA PARTIDA" />
    <qg:phrase text="Managers:" as="Técnicos:" />
    <qg:phrase text="World no." as="Mundo n.º" />
    <qg:phrase text="Save in slot" as="Guardar en" />
    <qg:phrase text="Manager's name:" as="Nombre del técnico:" />
    <qg:phrase text="Choose the manager's club:" as="Elige el club del técnico:" />
    <qg:phrase text="big" as="grande" />
    <qg:phrase text="middle" as="mediano" />
    <qg:phrase text="small" as="pequeño" />
    <qg:phrase text="Manager" as="Técnico" />
    <qg:phrase text="Start the league" as="Empezar la liga" />
    <qg:phrase text="Back" as="Volver" />
    <qg:phrase text="Round" as="Jornada" />
    <qg:phrase text="Balance:" as="Saldo:" />
    <qg:phrase text="Place:" as="Puesto:" />
    <qg:phrase text="place" as="puesto" />
    <qg:phrase text="Form:" as="Racha:" />
    <qg:phrase text="Morale:" as="Moral:" />
    <qg:phrase text="Ground:" as="Estadio:" />
    <qg:phrase text="seats" as="asientos" />
    <qg:phrase text="NEXT MATCH" as="PRÓXIMO PARTIDO" />
    <qg:phrase text="Panda League, round" as="Liga Panda, jornada" />
    <qg:phrase text="home" as="en casa" />
    <qg:phrase text="away" as="fuera" />
    <qg:phrase text="Objective:" as="Objetivo:" />
    <qg:phrase text="The line-up is not complete (F1)" as="La alineación no está completa (F1)" />
    <qg:phrase text="NEWS" as="NOTICIAS" />
    <qg:phrase text="Line-up" as="Alineación" />
    <qg:phrase text="Tactics" as="Tácticas" />
    <qg:phrase text="Squad" as="Plantilla" />
    <qg:phrase text="Finances" as="Finanzas" />
    <qg:phrase text="Table" as="Clasificación" />
    <qg:phrase text="Ready: next manager" as="Listo: siguiente técnico" />
    <qg:phrase text="Play the round" as="Jugar la jornada" />
    <qg:phrase text="Save and leave" as="Guardar y salir" />
    <qg:phrase text="The Panda League kicks off:" as="Empieza la Liga Panda:" />
    <qg:phrase text="They say a phenomenon plays in the lower divisions..." as="Dicen que un fenómeno juega en las divisiones de abajo..." />
    <qg:phrase text="Rumour: the hidden phenomenon would be a goalkeeper." as="Rumor: el fenómeno escondido sería un portero." />
    <qg:phrase text="Rumour: the hidden phenomenon would be a defender." as="Rumor: el fenómeno escondido sería un defensa." />
    <qg:phrase text="Rumour: the hidden phenomenon would be a midfielder." as="Rumor: el fenómeno escondido sería un centrocampista." />
    <qg:phrase text="Rumour: the hidden phenomenon would be a forward." as="Rumor: el fenómeno escondido sería un delantero." />
    <qg:phrase text="Revealed: the phenomenon plays for" as="Revelado: el fenómeno juega en" />
    <qg:phrase text="W" as="G" />
    <qg:phrase text="D" as="E" />
    <qg:phrase text="L" as="P" />
    <qg:phrase text="GK" as="POR" />
    <qg:phrase text="DF" as="DEF" />
    <qg:phrase text="MF" as="MED" />
    <qg:phrase text="FW" as="DEL" />
    <qg:phrase text="SQUAD" as="PLANTILLA" />
    <qg:phrase text="players, wages" as="jugadores, sueldos" />
    <qg:phrase text="/month" as="/mes" />
    <qg:phrase text="Name" as="Nombre" />
    <qg:phrase text="Pos" as="Pos" />
    <qg:phrase text="Str" as="Fue" />
    <qg:phrase text="Traits" as="ADN" />
    <qg:phrase text="Morale" as="Moral" />
    <qg:phrase text="Form" as="Forma" />
    <qg:phrase text="Goals" as="Goles" />
    <qg:phrase text="Fit" as="Est" />
    <qg:phrase text="Salary" as="Sueldo" />
    <qg:phrase text="Genius" as="Genio" />
    <qg:phrase text="Ace" as="Crack" />
    <qg:phrase text="Finisher" as="Goleador" />
    <qg:phrase text="Set pieces" as="Especialista" />
    <qg:phrase text="Leader" as="Líder" />
    <qg:phrase text="Star" as="Estrella" />
    <qg:phrase text="Wall" as="Muralla" />
    <qg:phrase text="LINE-UP" as="ALINEACIÓN" />
    <qg:phrase text="in the eleven:" as="titulares:" />
    <qg:phrase text="Plays" as="Juega" />
    <qg:phrase text="ELEVEN" as="TITULAR" />
    <qg:phrase text="bench" as="banquillo" />
    <qg:phrase text="Attack" as="Ataque" />
    <qg:phrase text="Defence" as="Defensa" />
    <qg:phrase text="eleven fit to play, one of them in goal" as="11 titulares disponibles, uno de ellos en la portería" />
    <qg:phrase text="Eleven → bench → out" as="Titular → banquillo → fuera" />
    <qg:phrase text="Automatic" as="Automática" />
    <qg:phrase text="TACTICS" as="TÁCTICAS" />
    <qg:phrase text="They tend to play:" as="Suele jugar:" />
    <qg:phrase text="Formation:" as="Formación:" />
    <qg:phrase text="Style:" as="Estilo:" />
    <qg:phrase text="AUTOMATIC CHANGES" as="CAMBIOS AUTOMÁTICOS" />
    <qg:phrase text="When" as="Si va" />
    <qg:phrase text="after" as="desde" />
    <qg:phrase text="change to" as="pasa a" />
    <qg:phrase text="winning" as="ganando" />
    <qg:phrase text="drawing" as="empatando" />
    <qg:phrase text="losing" as="perdiendo" />
    <qg:phrase text="Balanced" as="Equilibrado" />
    <qg:phrase text="Attacking" as="Ofensivo" />
    <qg:phrase text="All-out attack" as="Muy ofensivo" />
    <qg:phrase text="Defensive" as="Defensivo" />
    <qg:phrase text="Park the bus" as="Muy defensivo" />
    <qg:phrase text="Counter-attack" as="Contraataque" />
    <qg:phrase text="Kamikaze" as="Kamikaze" />
    <qg:phrase text="Win" as="Victoria" />
    <qg:phrase text="Draw" as="Empate" />
    <qg:phrase text="Avoid defeat" as="No perder" />
    <qg:phrase text="By hand" as="Decidir en el partido" />
    <qg:phrase text="Auto" as="Auto" />
    <qg:phrase text="Tactical edge" as="Ventaja táctica" />
    <qg:phrase text="Tactical handicap" as="Desventaja táctica" />
    <qg:phrase text="No tactical edge" as="Sin ventaja táctica" />
    <qg:phrase text="PANDA LEAGUE" as="LIGA PANDA" />
    <qg:phrase text="Club" as="Club" />
    <qg:phrase text="P" as="PJ" />
    <qg:phrase text="GF" as="GF" />
    <qg:phrase text="GA" as="GC" />
    <qg:phrase text="GD" as="DG" />
    <qg:phrase text="Pts" as="Pts" />
    <qg:phrase text="FINANCES" as="FINANZAS" />
    <qg:phrase text="Wages a month:" as="Sueldos al mes:" />
    <qg:phrase text="Wages a week:" as="Sueldos a la semana:" />
    <qg:phrase text="Last gate:" as="Última taquilla:" />
    <qg:phrase text="TV a month:" as="TV al mes:" />
    <qg:phrase text="Costs a month:" as="Gastos al mes:" />
    <qg:phrase text="Ticket:" as="Entrada:" />
    <qg:phrase text="Ticket" as="Entrada" />
    <qg:phrase text="first half" as="primera parte" />
    <qg:phrase text="second half" as="segunda parte" />
    <qg:phrase text="GOAL" as="GOL" />
    <qg:phrase text="injured" as="lesionado" />
    <qg:phrase text="LIVE ROUND" as="JORNADA EN DIRECTO" />
    <qg:phrase text="GOOOOOAL!" as="¡GOOOOOL!" />
    <qg:phrase text="AUTOMATIC CHANGE" as="CAMBIO TÁCTICO AUTOMÁTICO" />
    <qg:phrase text="Undo" as="Deshacer" />
    <qg:phrase text="Keep" as="Mantener" />
    <qg:phrase text="three seconds to undo it" as="3 segundos para deshacerlo" />
    <qg:phrase text="PAUSED" as="PAUSA" />
    <qg:phrase text="SPACE" as="ESPACIO" />
    <qg:phrase text="Go on" as="Seguir" />
    <qg:phrase text="Time-out" as="Pedir tiempo" />
    <qg:phrase text="Pause" as="Pausar" />
    <qg:phrase text="Speed" as="Velocidad" />
    <qg:phrase text="Another match" as="Otro partido" />
    <qg:phrase text="Tactics of" as="Tácticas de" />
    <qg:phrase text="ROUND" as="JORNADA" />
    <qg:phrase text="PLAYED" as="JUGADA" />
    <qg:phrase text="THE MANAGERS" as="LOS TÉCNICOS" />
    <qg:phrase text="End of the season" as="Fin de temporada" />
    <qg:phrase text="Next round" as="Siguiente jornada" />
    <qg:phrase text="CHAMPIONS" as="CAMPEONES" />
    <qg:phrase text="New season" as="Nueva temporada" />
    <qg:phrase text="To the title" as="Al título" />
    <qg:phrase text="Manager:" as="Técnico:" />
    <qg:phrase text="Sounds" as="Sonidos" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="Full screen" as="Pantalla completa" />
    <qg:phrase text="yes" as="sí" />
    <qg:phrase text="no" as="no" />
    <qg:phrase text="(up to a quarter more at home)." as="(hasta un cuarto más en casa)." />
    <qg:phrase text="A dearer ticket keeps people away:" as="Una entrada más cara aleja al público;" />
    <qg:phrase text="a full ground lifts the side" as="un estadio lleno empuja al equipo" />
    <qg:phrase text="Against it:" as="Contra eso:" />
    <qg:phrase text="Booked:" as="Amonestados:" />
    <qg:phrase text="Came on:" as="Entraron:" />
    <qg:phrase text="Crowd at this price:" as="Público con esta entrada:" />
    <qg:phrase text="Crowd:" as="Público:" />
    <qg:phrase text="Shots" as="Tiros" />
    <qg:phrase text="Ball" as="Posesión" />
    <qg:phrase text="Pressing:" as="Presión:" />
    <qg:phrase text="Gate:" as="Taquilla:" />
    <qg:phrase text="Injured:" as="Lesionados:" />
    <qg:phrase text="LAST MATCHES" as="ÚLTIMOS PARTIDOS" />
    <qg:phrase text="Last crowd:" as="Último público:" />
    <qg:phrase text="Man of the match:" as="Figura:" />
    <qg:phrase text="No matches yet." as="Aún sin partidos." />
    <qg:phrase text="Opponent:" as="Rival:" />
    <qg:phrase text="Out of the next match:" as="Fuera del próximo partido:" />
    <qg:phrase text="Sent off:" as="Expulsados:" />
    <qg:phrase text="Substitution" as="Cambio" />
    <qg:phrase text="TOP SCORERS" as="GOLEADORES" />
    <qg:phrase text="Tendency:" as="Tendencia:" />
    <qg:phrase text="Top scorer:" as="Goleador:" />
    <qg:phrase text="Who comes off?" as="¿Quién sale?" />
    <qg:phrase text="Who comes on for" as="¿Quién entra por" />
    <qg:phrase text="YOUR MATCH" as="TU PARTIDO" />
    <qg:phrase text="for" as="por" />
    <qg:phrase text="goal" as="gol" />
    <qg:phrase text="goals" as="goles" />
    <qg:phrase text="res" as="sup" />
    <qg:phrase text="sent off" as="expulsado" />
    <qg:phrase text="the keepers" as="los porteros" />
    <qg:phrase text="vs" as="vs" />
    <qg:phrase text="1st division" as="1ª división" />
    <qg:phrase text="2nd division" as="2ª división" />
    <qg:phrase text="3rd division" as="3ª división" />
    <qg:phrase text="4th division" as="4ª división" />
    <qg:phrase text="round" as="jornada" />
    <qg:phrase text="Sponsor a month:" as="Patrocinio al mes:" />
    <qg:phrase text="(a small club of the 4th division)" as="(un club pequeño de la 4ª división)" />
    <qg:phrase text="up and down" as="ascenso y descenso" />
    <qg:phrase text="Another division" as="Otra división" />
    <qg:phrase text="Promoted to the" as="Ascendió a la" />
    <qg:phrase text="Relegated to the" as="Descendió a la" />
    <qg:phrase text="UP AND DOWN" as="ASCENSOS Y DESCENSOS" />
    <qg:phrase text="to the" as="a la" />
    <qg:phrase text="promoted!" as="¡ascendió!" />
    <qg:phrase text="relegated." as="descendió." />
    <qg:phrase text="stays in the" as="se queda en la" />
    <qg:phrase text="of the" as="de la" />
    <qg:phrase text="This game was saved by the first PandaFoot" as="Esta partida la guardó el primer PandaFoot" />
    <qg:phrase text="(one league of ten clubs), which this one" as="(una liga de diez clubes), que este no" />
    <qg:phrase text="cannot continue. Start a new game: four" as="puede continuar. Empieza una nueva: cuatro" />
    <qg:phrase text="divisions, from a small club of the 4th." as="divisiones, desde un club pequeño de la 4ª." />
    <qg:phrase text="managers" as="técnicos" />
    <qg:phrase text="Division" as="División" />
    <qg:phrase text="Board:" as="Directiva:" />
    <qg:phrase text="The board is losing its patience" as="La directiva está perdiendo la paciencia" />
    <qg:phrase text="The board expects:" as="La directiva espera:" />
    <qg:phrase text="Sacked by the board of" as="Despedido por la directiva del" />
    <qg:phrase text="New manager of" as="Nuevo técnico del" />
    <qg:phrase text="SACKED" as="DESPEDIDO" />
    <qg:phrase text="AN OFFER" as="UNA OFERTA" />
    <qg:phrase text="The board has lost its patience." as="La directiva perdió la paciencia." />
    <qg:phrase text="Your work has been noticed." as="Tu trabajo llamó la atención." />
    <qg:phrase text="These clubs would have you:" as="Estos clubes te quieren:" />
    <qg:phrase text="No club would have you now." as="Ningún club te quiere ahora." />
    <qg:phrase text="Take" as="Dirigir al" />
    <qg:phrase text="expects" as="espera" />
    <qg:phrase text="Stay at" as="Quedarse en el" />
    <qg:phrase text="End the career" as="Terminar la carrera" />
    <qg:phrase text="THE END OF THE CAREER" as="FIN DE LA CARRERA" />
    <qg:phrase text="seasons" as="temporadas" />
    <qg:phrase text="titles" as="títulos" />
  </qg:language>
</q:application>
