<q:component name="Contact">
  <q:action name="send" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="message" required="true" minlength="5" />
    <q:mail to="support@example.com" reply_to="{email}" subject="Contact from {email}" type="text">{message}</q:mail>
    <q:redirect url="/" flash="Thanks! We will answer {email}." />
  </q:action>

  <h1>Contact us</h1>
  <q:if condition="flash"><p class="flash">{flash}</p></q:if>
  <form method="POST" action="/?action=send">
    <input name="email" type="email" />
    <textarea name="message"></textarea>
    <button>Send</button>
  </form>
</q:component>
