<!-- Chat Messages Partial - renders only the message list for HTMX polling -->
<q:component name="ChatMessages" xmlns:q="https://quantum.lang/ns">

  <q:if condition="{application.chatMessages.length} == 0">
    <div style="text-align: center; color: #999; padding: 60px 20px;">
      <p style="font-size: 16px; margin: 0;">No messages yet. Start the conversation!</p>
    </div>
  </q:if>

  <q:loop type="array" var="msg" items="{application.chatMessages}" index="idx">
    <div style="margin-bottom: 8px;">
      <div style="background: white; padding: 10px 16px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); max-width: 70%; word-wrap: break-word; font-size: 14px; line-height: 1.5; display: inline-block;">
        {msg}
      </div>
    </div>
  </q:loop>

</q:component>
