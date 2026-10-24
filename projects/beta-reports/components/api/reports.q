<q:component name="reports" xmlns:q="https://quantum.lang/ns">
  <!-- POST /api/reports: a report from inside a game (a bug, a suggestion or anything else), kept, and told as
       an issue in the forge's repository, the save beside it. The games' site may post from a browser; a game
       on the desktop sends no Origin. -->
  <q:endpoint method="POST" origins="https://quantumframework.net" limit="20/hour" maxsize="4mb">
    <q:param name="game" type="string" required="true" pattern="^[a-z0-9-]{1,40}$" />
    <q:param name="version" type="string" required="true" maxlength="20" />
    <q:param name="kind" type="string" required="true" enum="bug,suggestion,other" />
    <q:param name="text" type="string" required="true" minlength="3" maxlength="4000" />
    <q:param name="screen" type="string" maxlength="60" default="" />
    <q:param name="option" type="string" maxlength="120" default="" />
    <q:param name="context" type="string" maxlength="2000" default="" />
    <q:param name="player" type="string" maxlength="40" default="" />
    <q:param name="save" type="string" maxlength="3500000" default="" />

    <q:query name="kept" datasource="reports">
      INSERT INTO reports (game, version, kind, text, screen, option, context, player, save)
      VALUES (:game, :version, :kind, :text, :screen, :option, :context, :player, :save) RETURNING id
      <q:param name="game" value="{game}" type="string" />
      <q:param name="version" value="{version}" type="string" />
      <q:param name="kind" value="{kind}" type="string" />
      <q:param name="text" value="{text}" type="string" />
      <q:param name="screen" value="{screen}" type="string" />
      <q:param name="option" value="{option}" type="string" />
      <q:param name="context" value="{context}" type="string" />
      <q:param name="player" value="{player}" type="string" />
      <q:param name="save" value="{save}" type="string" />
    </q:query>
    <q:set name="number" value="{kept[0].id}" />
    <q:query name="where" datasource="reports">SELECT forge, repo, branch FROM settings WHERE id = 1</q:query>
    <q:set name="savePath" value="beta-reports/{game}/{number}.json" />

    <!-- the save, a file of the repository (an issue holds 64 KB, a save more) -->
    <q:if condition="{save != ''}">
      <q:invoke name="saved" url="{where[0].forge}/repos/{where[0].repo}/contents/{savePath}" method="PUT"
                authType="bearer" authToken="${GITHUB_TOKEN}" timeout="20000" onerror="continue">
        <q:header name="Accept" value="application/vnd.github+json" />
        <q:body>{ {'message': 'Report ' + str(number) + ' (' + game + ' ' + version + '): the save',
                   'content': base64(save), 'branch': where[0].branch} }</q:body>
      </q:invoke>
    </q:if>

    <q:set name="title" value="{'[' + game + ' ' + version + '] ' + kind + ': ' + (text[0:70] + '...' if len(text) > 70 else text)}" />
    <q:set name="told" value="{'**' + kind + '** in ' + game + ' ' + version + (' (' + screen + ')' if screen else '') + (', on “' + option + '”' if option else '') + (', by ' + player if player else '') + '\n\n> ' + replace(text, '\n', '\n> ') + '\n\n' + ('Where the game was: ' + context + '\n\n' if context else '') + ('The save: `' + savePath + '` on the branch `' + where[0].branch + '`\n\n' if save else '') + 'Report ' + str(number) + ' of the receiver.'}" />
    <q:invoke name="issue" url="{where[0].forge}/repos/{where[0].repo}/issues" method="POST"
              authType="bearer" authToken="${GITHUB_TOKEN}" timeout="20000" onerror="continue">
      <q:header name="Accept" value="application/vnd.github+json" />
      <q:body>{ {'title': title, 'body': told, 'labels': ['beta-report', game, kind]} }</q:body>
    </q:invoke>
    <q:if condition="{issue_result.success}">
      <q:query datasource="reports">
        UPDATE reports SET issue = :issue WHERE id = :id
        <q:param name="issue" value="{issue.number}" type="integer" />
        <q:param name="id" value="{number}" type="integer" />
      </q:query>
    </q:if>

    <q:respond status="201" json="{ {'number': number} }" />
  </q:endpoint>
</q:component>
