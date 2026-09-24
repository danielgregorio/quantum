<q:application id="file-browser" type="terminal">
  <qt:css>
    #file-tree { width: 40; border: solid green; }
    #preview { height: 1fr; border: solid #444; }
  </qt:css>

  <qt:screen name="browser" title="File Browser">
    <qt:header title="Quantum File Browser"/>
    <qt:layout direction="horizontal">
      <qt:tree id="file-tree" label="." on-select="on_file_select"/>
      <qt:panel id="preview" title="Preview">
        <qt:text id="file-content">Select a file...</qt:text>
      </qt:panel>
    </qt:layout>
    <qt:footer/>
    <qt:keybinding key="q" action="quit" description="Quit"/>
    <qt:keybinding key="r" action="refresh_tree" description="Refresh"/>
  </qt:screen>
</q:application>
