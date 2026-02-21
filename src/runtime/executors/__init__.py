"""
Quantum Executors Package

Modular executors for AST node execution. Each executor handles specific node types.

Categories:
- control_flow: if, loop, set
- data: query, invoke, data, transaction
- services: log, dump, file, mail
- ai: llm, agent, team, knowledge
- messaging: websocket, message, queue, subscribe
- jobs: schedule, thread, job
- scripting: python, pyimport, pyclass
"""

from .base import BaseExecutor, ExecutorError

# Control flow executors
from .control_flow import IfExecutor, LoopExecutor, SetExecutor

# Data executors
from .data import QueryExecutor, InvokeExecutor, DataExecutor, TransactionExecutor

# Service executors
from .services import LogExecutor, DumpExecutor, FileExecutor, MailExecutor

# AI executors
from .ai import LLMExecutor, AgentExecutor, TeamExecutor, KnowledgeExecutor

# Messaging executors
from .messaging import (
    WebSocketExecutor, WebSocketSendExecutor, WebSocketCloseExecutor,
    MessageExecutor, SubscribeExecutor, QueueExecutor
)

# Jobs executors
from .jobs import ScheduleExecutor, ThreadExecutor, JobExecutor

# Scripting executors
from .scripting import PythonExecutor, PyImportExecutor, PyClassExecutor


__all__ = [
    # Base
    'BaseExecutor', 'ExecutorError',

    # Control flow
    'IfExecutor', 'LoopExecutor', 'SetExecutor',

    # Data
    'QueryExecutor', 'InvokeExecutor', 'DataExecutor', 'TransactionExecutor',

    # Services
    'LogExecutor', 'DumpExecutor', 'FileExecutor', 'MailExecutor',

    # AI
    'LLMExecutor', 'AgentExecutor', 'TeamExecutor', 'KnowledgeExecutor',

    # Messaging
    'WebSocketExecutor', 'WebSocketSendExecutor', 'WebSocketCloseExecutor',
    'MessageExecutor', 'SubscribeExecutor', 'QueueExecutor',

    # Jobs
    'ScheduleExecutor', 'ThreadExecutor', 'JobExecutor',

    # Scripting
    'PythonExecutor', 'PyImportExecutor', 'PyClassExecutor',
]

__version__ = '1.0.0'
