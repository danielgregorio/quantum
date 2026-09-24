<q:application id="server-dashboard" type="terminal">
  <qt:css>
    #cpu-panel { border: solid green; height: 1fr; }
    #log-panel { border: solid yellow; height: 2fr; }
  </qt:css>

  <qt:screen name="main" title="Server Dashboard">
    <qt:header title="Server Dashboard" show-clock="true"/>
    <q:set name="refresh_count" type="number" value="0"/>
    <q:set name="cpu_pct" type="number" value="42"/>

    <qt:layout direction="horizontal">
      <qt:panel id="cpu-panel" title="CPU Usage">
        <qt:progress id="cpu-bar" total="100" value-var="cpu_pct"/>
        <qt:text>{cpu_pct}% used</qt:text>
      </qt:panel>
    </qt:layout>

    <qt:panel id="log-panel" title="Processes">
      <qt:table id="proc-table" zebra="true">
        <qt:column name="PID" key="pid" width="10"/>
        <qt:column name="Process" key="name" width="30"/>
        <qt:column name="CPU %" key="cpu_percent" align="right"/>
      </qt:table>
    </qt:panel>

    <qt:footer/>
    <qt:keybinding key="q" action="quit" description="Quit"/>
    <qt:keybinding key="r" action="refresh_data" description="Refresh"/>
    <qt:timer id="auto-refresh" interval="5.0" action="refresh_data"/>
  </qt:screen>
</q:application>
