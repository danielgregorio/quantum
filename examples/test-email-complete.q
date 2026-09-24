<!-- Test Email Complete -->
<!-- Demonstrates all q:mail patterns for email sending -->
<q:component name="TestEmailComplete" xmlns:q="https://quantum.lang/ns">

  <!-- Simple text email -->
  <q:mail name="simpleEmail"
          to="user@example.com"
          from="noreply@myapp.com"
          subject="Welcome to MyApp">
    Hello! Welcome to our application.
    Thank you for signing up.
  </q:mail>

  <!-- HTML email -->
  <q:mail name="htmlEmail"
          to="user@example.com"
          from="noreply@myapp.com"
          subject="Your Weekly Newsletter"
          type="html">
    <![CDATA[
    <html>
      <body>
        <h1>Weekly Newsletter</h1>
        <p>Here are this week's updates...</p>
      </body>
    </html>
    ]]>
  </q:mail>

  <!-- Email with CC and BCC -->
  <q:mail name="ccEmail"
          to="main@example.com"
          cc="copy@example.com"
          bcc="hidden@example.com"
          from="sender@myapp.com"
          subject="Team Update">
    This email is sent to multiple recipients.
  </q:mail>

  <!-- Email with Reply-To -->
  <q:mail name="replyToEmail"
          to="user@example.com"
          from="noreply@myapp.com"
          replyTo="support@myapp.com"
          subject="Support Request Received">
    We received your support request.
    Reply to this email to continue the conversation.
  </q:mail>

  <q:return value="Email templates defined: simpleEmail, htmlEmail, ccEmail, replyToEmail" />
</q:component>
