<q:application id="dashboard" type="terminal">
  <qt:css>
    #main-panel { border: solid green; }
  </qt:css>
  <qt:screen name="main" title="Dashboard">
    <qt:header title="Dashboard" show-clock="true"/>
    <qt:layout direction="horizontal">
      <qt:panel id="main-panel" title="Info">
        <qt:progress id="bar" total="100" value-var="pct"/>
        <qt:text>{pct}%</qt:text>
      </qt:panel>
    </qt:layout>
    <qt:footer/>
    <qt:keybinding key="q" action="quit" description="Quit"/>
  </qt:screen>
</q:application>
