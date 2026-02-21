"""
Quantum Parsers Package

Modular parsers for XML tag parsing. Each parser handles specific tag types.

Categories:
- control_flow: if, loop, set
- data: query, invoke, data, transaction
- services: log, dump, file, mail
- ai: llm, agent, team, knowledge
- messaging: websocket, message, subscribe, queue
- jobs: schedule, thread, job
- scripting: python, pyimport, pyclass
"""

from .base import BaseTagParser, ParserError

# Control flow parsers
from .control_flow import IfParser, LoopParser, SetParser

# Data parsers
from .data import QueryParser, InvokeParser, DataParser, TransactionParser

# Service parsers
from .services import LogParser, DumpParser, FileParser, MailParser

# AI parsers
from .ai import LLMParser, AgentParser, TeamParser, KnowledgeParser

# Messaging parsers
from .messaging import (
    WebSocketParser, WebSocketSendParser, WebSocketCloseParser,
    MessageParser, SubscribeParser, QueueParser
)

# Jobs parsers
from .jobs import ScheduleParser, ThreadParser, JobParser

# Scripting parsers
from .scripting import PythonParser, PyImportParser, PyClassParser

# HTML parsers
from .html import HTMLParser, ComponentCallParser


__all__ = [
    # Base
    'BaseTagParser', 'ParserError',

    # Control flow
    'IfParser', 'LoopParser', 'SetParser',

    # Data
    'QueryParser', 'InvokeParser', 'DataParser', 'TransactionParser',

    # Services
    'LogParser', 'DumpParser', 'FileParser', 'MailParser',

    # AI
    'LLMParser', 'AgentParser', 'TeamParser', 'KnowledgeParser',

    # Messaging
    'WebSocketParser', 'WebSocketSendParser', 'WebSocketCloseParser',
    'MessageParser', 'SubscribeParser', 'QueueParser',

    # Jobs
    'ScheduleParser', 'ThreadParser', 'JobParser',

    # Scripting
    'PythonParser', 'PyImportParser', 'PyClassParser',

    # HTML
    'HTMLParser', 'ComponentCallParser',
]

__version__ = '1.0.0'
