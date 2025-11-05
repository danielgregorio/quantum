<q:component name="TestEmailRecipients">
  <!-- Test: Email with multiple recipients (to, cc, bcc) -->

  <q:set name="projectName" value="Quantum Framework" />

  <q:mail to="team@example.com"
          cc="manager@example.com"
          bcc="archive@example.com"
          from="noreply@quantum.dev"
          replyTo="support@quantum.dev"
          subject="Project Update: {projectName}">
    Team,

    Here's the latest update on {projectName}.

    Phase 1-12 completed successfully!

    Best regards,
    Project Manager
  </q:mail>

  <!-- Expected: Email sent to multiple recipients -->
  Email sent with CC and BCC recipients
</q:component>
