<!-- The Hive's screen: what hive-screen draws on the machine's console, and what happens in it when
     the Hive's events arrive. Compiles to screen.toml and font.png next to this file
     (python scripts/generate-screen-config.py), which hive-screen loads from /etc/hive/screen/. -->
<q:application id="hive-screen" type="screen">

  <!-- the cells of the honeycomb: 24x24 frames, drawn by scripts/art/hive_screen.py -->
  <qs:sheet name="cell" src="art/cells.png" tile="24">
    <qs:animation name="smoke" frames="2,3,4,5,6,2" fps="4" loop="false" />
    <qs:animation name="worry" frames="7,1" fps="2" />
  </qs:sheet>
  <qs:sheet name="bee" src="art/bee.png" tile="16">
    <qs:animation name="fly" frames="0,1" fps="10" />
  </qs:sheet>

  <qs:particles name="stars" preset="stars" />
  <qs:particles name="dust" preset="dust" color="#8a7a5a" />
  <qs:particles name="snow" preset="snow" amount="24" color="#c8d0f0" />

  <qs:scene width="320" height="180" background="#1a1a2e">
    <!-- the fine level, which the daemon affords with the machine's cores: snow over the scene -->
    <qs:emitter particles="snow" x="0" y="0" width="320" level="2" />
    <!-- the bar at the top: the machine, its cores, the level the screen is at and the time -->
    <qs:bar side="top" title="Quantum OS" left="{host}" right="{cores} cores · {level} · {clock}" />

    <!-- one cell a service the whitelist names; a cell fills with honey when the Hive restarts it -->
    <qs:sprite name="nginx" sheet="cell" frame="1" x="6" y="18" />
    <qs:text value="nginx" x="34" y="24" />
    <qs:sprite name="apache2" sheet="cell" frame="1" x="6" y="46" />
    <qs:text value="apache2" x="34" y="52" />
    <qs:sprite name="postgresql" sheet="cell" frame="1" x="6" y="74" />
    <qs:text value="postgresql" x="34" y="80" />
    <qs:sprite name="mysql" sheet="cell" frame="1" x="6" y="102" />
    <qs:text value="mysql" x="34" y="108" />
    <qs:sprite name="redis-server" sheet="cell" frame="1" x="98" y="18" />
    <qs:text value="redis" x="126" y="24" />
    <qs:sprite name="mongodb" sheet="cell" frame="1" x="98" y="46" />
    <qs:text value="mongodb" x="126" y="52" />
    <qs:sprite name="docker" sheet="cell" frame="1" x="98" y="74" />
    <qs:text value="docker" x="126" y="80" />
    <qs:sprite name="containerd" sheet="cell" frame="1" x="98" y="102" />
    <qs:text value="containerd" x="126" y="108" />
    <qs:sprite name="bee" sheet="bee" x="168" y="36" animation="fly" />

    <!-- the offers and the notices as panels with their own title bars -->
    <qs:offers title="Offers" x="188" y="18" width="126" rows="9" />
    <qs:notices title="Notices" x="6" y="132" width="308" rows="2" />
    <!-- the bar at the bottom: what the Hive said last shows here while it lasts -->
    <qs:bar side="bottom" right="offers: {offers} · F1" />
  </qs:scene>

  <qs:on event="service-crash">
    <qs:animate target="{service}" name="smoke" />
    <qs:emit particles="dust" at="{service}" dx="12" dy="12" />
    <qs:say text="{service} stopped (exit {exit_code})" />
  </qs:on>
  <qs:on event="log-anomaly">
    <qs:animate target="{service}" name="worry" />
    <qs:say text="{service} is logging errors" />
  </qs:on>
  <qs:on event="port-conflict">
    <qs:say text="port {port}: {requester} wanted it, {holder} holds it" />
  </qs:on>
  <qs:on event="disk-low">
    <qs:say text="{mount} is {percent}% full, {free_mb} MB free" />
  </qs:on>
  <qs:on event="memory-pressure">
    <qs:say text="memory: {free_mb} of {total_mb} MB free" />
  </qs:on>
  <qs:on event="command-observed">
    <qs:say text="watched: {cmd}" />
  </qs:on>
  <qs:on event="command-not-found">
    <qs:say text="{command}: not installed; {package} would provide it" />
  </qs:on>
  <qs:on event="notice">
    <qs:say text="{title}: {body}" />
  </qs:on>
  <qs:on event="request">
    <qs:emit particles="stars" at="bee" dx="8" dy="8" />
    <qs:say text="{user} asks: {what}; Enter approves, Escape dismisses" seconds="6" />
  </qs:on>
  <qs:on event="offer">
    <qs:emit particles="stars" at="bee" dx="8" dy="8" />
    <qs:tween target="bee" property="y" to="42" from="36" seconds="0.4" trans="sine" ease="in-out" repeat="3" yoyo="true" />
    <qs:say text="the Hive offers {count}: up and down choose, Enter approves, Escape dismisses" seconds="6" />
  </qs:on>
  <qs:on event="done">
    <qs:frame target="{service}" frame="0" />
    <qs:emit particles="stars" at="{service}" dx="12" dy="12" />
    <qs:say text="{action}: done" />
  </qs:on>
  <qs:on event="failed">
    <qs:say text="{action} failed: {output}" seconds="8" />
  </qs:on>
</q:application>
