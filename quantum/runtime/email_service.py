"""
Email for q:mail: SMTP through quantum.config.yaml's `mail:` (MAIL-1).
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
from pathlib import Path


logger = logging.getLogger('quantum.mail')
_HOSTNAME = None


def _local_hostname() -> str:
    """The name this machine greets the server with (EHLO).

    smtplib's default is socket.getfqdn(), a reverse DNS lookup on every
    connection: measured at 12 s for the first message on a Windows machine."""
    global _HOSTNAME
    if _HOSTNAME is None:
        import socket
        _HOSTNAME = socket.gethostname() or 'localhost'
    return _HOSTNAME


class EmailError(Exception):
    """Raised when email sending fails"""
    pass


class EmailService:
    """Sends q:mail through the server in quantum.config.yaml's `mail:` (MAIL-1).

    It used to read SMTP_* variables and, unless EMAIL_MOCK=false was set,
    print "[MOCK] Email sent" and answer success — so an application in
    production reported every e-mail as sent and sent none.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        mail = (config or {}).get('mail')
        self.configured = isinstance(mail, dict)
        mail = mail if self.configured else {}
        self.host = str(mail.get('host') or '').strip()
        self.port = int(mail.get('port') or 587)
        self.username = str(mail.get('username') or '')
        self.password = str(mail.get('password') or '')
        self.tls = str(mail.get('tls', True)).strip().lower() not in ('false', '0', 'no', 'off', '')
        self.default_from = str(mail.get('from') or '').strip()
        self.timeout = int(mail.get('timeout') or 30)

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_addr: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        reply_to: Optional[str] = None,
        email_type: str = "html",
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send one message; EmailError says why it was not sent."""
        if not self.configured or not self.host:
            raise EmailError(
                "q:mail needs a mail server: add `mail:` with host, port and from to "
                "quantum.config.yaml — or `host: log` in development, which writes each "
                "message to the log (MAIL-1)")
        sender = from_addr or self.default_from
        if not sender:
            raise EmailError("q:mail has no sender: set from= on the tag or `from:` under `mail:` (MAIL-1)")
        recipients = self._parse_recipients(to, cc, bcc)
        if not recipients:
            raise EmailError("q:mail has no recipient: to= is empty")

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = to
        msg['Subject'] = subject
        if cc:
            msg['Cc'] = cc
        if reply_to:
            msg['Reply-To'] = reply_to
        msg.attach(MIMEText(body, 'html' if email_type == 'html' else 'plain', 'utf-8'))
        for file_path in attachments or []:
            self._attach_file(msg, file_path)

        result = {'success': True, 'to': to, 'subject': subject, 'recipients': recipients}
        if self.host == 'log':
            logger.info("q:mail (host: log, not sent)\nFrom: %s\nTo: %s\nSubject: %s\n\n%s",
                        sender, ', '.join(recipients), subject, body)
            return {**result, 'logged': True}
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout,
                              local_hostname=_local_hostname()) as server:
                if self.tls:
                    server.starttls()
                if self.username:
                    server.login(self.username, self.password)
                refused = server.sendmail(sender, recipients, msg.as_string())
        except smtplib.SMTPRecipientsRefused as e:
            raise EmailError(f"the mail server {self.host}:{self.port} refused every recipient: "
                             f"{self._reasons(e.recipients)}") from e
        except (smtplib.SMTPException, OSError) as e:
            raise EmailError(f"the mail server {self.host}:{self.port} did not take the message: {e}") from e
        if refused:
            # Some recipients got it: that is not a success to report as one.
            raise EmailError(f"the mail server {self.host}:{self.port} refused {self._reasons(refused)}")
        return result

    @staticmethod
    def _reasons(refused: Dict[str, Any]) -> str:
        return '; '.join(f"{addr} ({code} {msg.decode() if isinstance(msg, bytes) else msg})"
                         for addr, (code, msg) in refused.items())

    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """Attach a file to email message"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise EmailError(f"Attachment file not found: {file_path}")

            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {path.name}'
            )

            msg.attach(part)
        except Exception as e:
            raise EmailError(f"Failed to attach file {file_path}: {e}")

    def _parse_recipients(
        self,
        to: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> List[str]:
        """Parse comma-separated email addresses into list"""
        recipients = []

        if to:
            recipients.extend([e.strip() for e in to.split(',') if e.strip()])
        if cc:
            recipients.extend([e.strip() for e in cc.split(',') if e.strip()])
        if bcc:
            recipients.extend([e.strip() for e in bcc.split(',') if e.strip()])

        return recipients
