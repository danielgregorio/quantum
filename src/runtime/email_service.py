"""
Phase I: Email Service

ColdFusion cfmail-inspired email sending with SMTP support.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
from pathlib import Path


class EmailError(Exception):
    """Raised when email sending fails"""
    pass


class EmailService:
    """Service for sending emails via SMTP"""

    def __init__(self):
        """Initialize email service with config from environment"""
        self.smtp_host = os.getenv('SMTP_HOST', 'localhost')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.default_from = os.getenv('SMTP_FROM', 'noreply@quantum.dev')

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
        """
        Send email via SMTP

        Args:
            to: Recipient email(s) (comma-separated)
            subject: Email subject
            body: Email body content
            from_addr: Sender email (uses default if not provided)
            cc: CC recipients (comma-separated)
            bcc: BCC recipients (comma-separated)
            reply_to: Reply-To address
            email_type: 'html' or 'text'
            attachments: List of file paths to attach

        Returns:
            Dict with send result

        Raises:
            EmailError: If sending fails
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_addr or self.default_from
            msg['To'] = to
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = cc
            if reply_to:
                msg['Reply-To'] = reply_to

            # Attach body
            mime_type = 'html' if email_type == 'html' else 'plain'
            msg.attach(MIMEText(body, mime_type, 'utf-8'))

            # Attach files if provided
            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)

            # Prepare recipients
            recipients = self._parse_recipients(to, cc, bcc)

            # Send email
            if os.getenv('EMAIL_MOCK', 'true').lower() == 'true':
                # Mock mode for development (don't actually send)
                print(f"📧 [MOCK] Email sent to {to}")
                print(f"   Subject: {subject}")
                print(f"   From: {msg['From']}")
                print(f"   Type: {email_type}")
                return {
                    'success': True,
                    'mock': True,
                    'to': to,
                    'subject': subject,
                    'message': 'Email mock-sent successfully'
                }
            else:
                # Real SMTP sending
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.smtp_use_tls:
                        server.starttls()

                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)

                    server.sendmail(msg['From'], recipients, msg.as_string())

                return {
                    'success': True,
                    'to': to,
                    'subject': subject,
                    'message': 'Email sent successfully'
                }

        except Exception as e:
            raise EmailError(f"Failed to send email: {e}")

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
            recipients.extend([email.strip() for email in to.split(',')])
        if cc:
            recipients.extend([email.strip() for email in cc.split(',')])
        if bcc:
            recipients.extend([email.strip() for email in bcc.split(',')])

        return recipients
