<q:component name="TestEmailBasic">
  <!-- Test: Basic email sending -->

  <q:set name="recipientEmail" value="user@example.com" />
  <q:set name="userName" value="John Doe" />

  <q:mail to="{recipientEmail}"
          from="noreply@quantum.dev"
          subject="Welcome to Quantum!">
    Hello {userName},

    Welcome to Quantum Language Framework!

    Best regards,
    The Quantum Team
  </q:mail>

  <!-- Expected: Email sent successfully -->
  Email sent to {recipientEmail}
</q:component>
