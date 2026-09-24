<!-- Quantum Chat: join, talk, leave. Messages live in the application scope,
     so a second visitor would see them; each test starts with a new server. -->

<q:test name="the login screen" page="/">
  <test:visit />
  <test:expect text="Enter your name to join the conversation" />
</q:test>

<q:test name="join, send and leave" page="/">
  <test:submit action="join" username="Ana" />
  <test:expect redirect="/" />
  <test:expect text="Hello, Ana" />
  <test:expect text="No messages yet" />

  <test:submit action="send" message="Hello, everyone" />
  <test:expect redirect="/" />
  <test:expect text="Ana: Hello, everyone" />
  <test:expect no-text="No messages yet" />

  <test:visit path="/_partial/chat-messages" />
  <test:expect text="Ana: Hello, everyone" />

  <test:visit path="/" />
  <test:submit action="leave" />
  <test:expect text="Enter your name to join the conversation" />
</q:test>

<q:test name="an empty message is refused" page="/">
  <test:submit action="join" username="Ana" />
  <test:submit action="send" message="" />
  <test:expect error="message" />
</q:test>

<q:test name="sending without joining" page="/">
  <test:submit action="send" message="hi" />
  <test:expect flash="Join the chat first." />
  <test:expect no-text="hi" />
</q:test>
