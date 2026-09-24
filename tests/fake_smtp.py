"""A mail server that keeps what it receives, over real SMTP, for tests.

    with FakeSMTP() as smtp:
        ... mail: {host: 127.0.0.1, port: smtp.port, tls: false} ...
        smtp.messages   # [email.message.Message, ...] with .envelope_to
"""

import email
import socketserver
import threading
from email import policy


class _Handler(socketserver.StreamRequestHandler):
    def reply(self, line):
        self.wfile.write((line + '\r\n').encode())

    def handle(self):
        server = self.server
        self.reply('220 fake-smtp ready')
        sender, recipients = None, []
        while True:
            line = self.rfile.readline().decode('utf-8', 'replace')
            if not line:
                return
            command = line.strip().upper()
            if command.startswith(('HELO', 'EHLO')):
                self.reply('250 fake-smtp')
            elif command.startswith('MAIL FROM:'):
                sender, recipients = line.strip()[10:].strip(' <>'), []
                self.reply('250 OK')
            elif command.startswith('RCPT TO:'):
                if server.refuse:
                    self.reply('550 ' + server.refuse)
                    continue
                recipients.append(line.strip()[8:].strip(' <>'))
                self.reply('250 OK')
            elif command == 'DATA':
                self.reply('354 End data with <CR><LF>.<CR><LF>')
                data = []
                while True:
                    part = self.rfile.readline()
                    if part in (b'.\r\n', b'.\n', b''):
                        break
                    data.append(part[1:] if part.startswith(b'..') else part)
                message = email.message_from_bytes(b''.join(data), policy=policy.default)
                message.envelope_from, message.envelope_to = sender, recipients
                server.messages.append(message)
                self.reply('250 OK: queued')
            elif command == 'QUIT':
                self.reply('221 Bye')
                return
            else:
                self.reply('250 OK')


class FakeSMTP:
    def __init__(self):
        self.server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), _Handler)
        self.server.daemon_threads = True
        self.server.messages = []
        self.server.refuse = None             # e.g. 'mailbox unavailable'
        self.port = self.server.server_address[1]

    @property
    def messages(self):
        return self.server.messages

    def refuse(self, reason):
        self.server.refuse = reason

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
