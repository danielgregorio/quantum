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

  <qs:scene width="320" height="180" background="#1a1a2e">
    <qs:text value="Quantum OS" x="6" y="4" color="#ffd34d" />
    <qs:text value="the Hive" x="72" y="4" color="#8a8aa0" />
    <qs:sprite name="bee" sheet="bee" x="296" y="2" animation="fly" />

    <!-- one cell a service the whitelist names; a cell fills with honey when the Hive restarts it -->
    <qs:sprite name="nginx" sheet="cell" frame="1" x="6" y="22" />
    <qs:text value="nginx" x="34" y="29" />
    <qs:sprite name="apache2" sheet="cell" frame="1" x="6" y="52" />
    <qs:text value="apache2" x="34" y="59" />
    <qs:sprite name="postgresql" sheet="cell" frame="1" x="6" y="82" />
    <qs:text value="postgresql" x="34" y="89" />
    <qs:sprite name="mysql" sheet="cell" frame="1" x="6" y="112" />
    <qs:text value="mysql" x="34" y="119" />
    <qs:sprite name="redis-server" sheet="cell" frame="1" x="102" y="22" />
    <qs:text value="redis" x="130" y="29" />
    <qs:sprite name="mongodb" sheet="cell" frame="1" x="102" y="52" />
    <qs:text value="mongodb" x="130" y="59" />
    <qs:sprite name="docker" sheet="cell" frame="1" x="102" y="82" />
    <qs:text value="docker" x="130" y="89" />
    <qs:sprite name="containerd" sheet="cell" frame="1" x="102" y="112" />
    <qs:text value="containerd" x="130" y="119" />

    <qs:text value="Offers" x="186" y="22" color="#ffd34d" />
    <qs:offers x="186" y="34" width="130" rows="8" />
    <qs:notices x="6" y="142" width="308" rows="2" />
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
  <qs:on event="offer">
    <qs:emit particles="stars" at="bee" dx="8" dy="8" />
    <qs:tween target="bee" property="y" to="8" from="2" seconds="0.4" trans="sine" ease="in-out" repeat="3" yoyo="true" />
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
