<q:application id="llm-chat" type="terminal">
  <qt:css>
    #chat-log { height: 1fr; border: solid #444; }
    #input-bar { dock: bottom; height: 3; }
  </qt:css>

  <qt:screen name="chat" title="Quantum Chat">
    <qt:header title="Quantum Chat - Ollama"/>
    <q:set name="model" value="llama3"/>
    <q:set name="history" type="array" value="[]"/>

    <qt:log id="chat-log" auto-scroll="true" markup="true"/>
    <qt:layout direction="horizontal" id="input-bar">
      <qt:input id="user-input" placeholder="Type a message..." on-submit="send_message"/>
      <qt:button id="send-btn" label="Send" variant="primary" on-click="send_message"/>
    </qt:layout>

    <qt:footer/>
    <qt:keybinding key="ctrl+c" action="quit" description="Quit"/>

    <q:function name="send_message">
      <q:set name="placeholder" value="send_message action"/>
    </q:function>
  </qt:screen>
</q:application>
