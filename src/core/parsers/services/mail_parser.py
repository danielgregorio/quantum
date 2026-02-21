"""
Mail Parser - Parse q:mail statements

Handles email sending.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import MailNode


class MailParser(BaseTagParser):
    """
    Parser for q:mail statements.

    Supports:
    - HTML and plain text emails
    - CC, BCC, Reply-To
    - Attachments
    """

    @property
    def tag_names(self) -> List[str]:
        return ['mail']

    def parse(self, element: ET.Element) -> MailNode:
        """
        Parse q:mail statement.

        Args:
            element: XML element for q:mail

        Returns:
            MailNode AST node
        """
        to = self.get_attr(element, 'to')
        subject = self.get_attr(element, 'subject')

        if not to:
            raise ParserError("Mail requires 'to' attribute")
        if not subject:
            raise ParserError("Mail requires 'subject' attribute")

        mail_node = MailNode(to, subject)

        # Get body from content or attribute
        mail_node.body = self.get_text(element) or self.get_attr(element, 'body', '')

        # Optional attributes
        mail_node.from_addr = self.get_attr(element, 'from')
        mail_node.cc = self.get_attr(element, 'cc')
        mail_node.bcc = self.get_attr(element, 'bcc')
        mail_node.reply_to = self.get_attr(element, 'replyTo')
        mail_node.type = self.get_attr(element, 'type', 'html')

        # Parse attachments
        for child in element:
            child_type = self.get_element_name(child)
            if child_type == 'attachment':
                attachment = self.get_attr(child, 'file')
                if attachment:
                    mail_node.attachments.append(attachment)

        return mail_node
