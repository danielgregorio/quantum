"""
AST Nodes for LLM Feature

Represents q:llm tags in the AST.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class LLMNode:
    """
    Represents a <q:llm> tag - defines an LLM configuration

    Example:
        <q:llm id="assistant" model="llama3" provider="ollama" temperature="0.7">
            <default-prompt>You are a helpful AI assistant.</default-prompt>
        </q:llm>

    Attributes:
        llm_id: Unique identifier for this LLM configuration
        model: Model name (e.g., "llama3", "codellama:13b", "gpt-4")
        provider: LLM provider ("ollama", "openai", "anthropic")
        temperature: Temperature setting (0.0-1.0)
        max_tokens: Maximum tokens to generate
        system_prompt: System/default prompt for the LLM
        options: Additional provider-specific options
    """
    llm_id: str
    model: str
    provider: str = "ollama"  # Default to Ollama
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        """Validate LLM configuration"""
        errors = []

        if not self.llm_id:
            errors.append("LLM must have an 'id' attribute")

        if not self.model:
            errors.append("LLM must have a 'model' attribute")

        if self.temperature < 0 or self.temperature > 1:
            errors.append(f"Temperature must be between 0 and 1, got {self.temperature}")

        if self.provider not in ["ollama", "openai", "anthropic", "auto"]:
            errors.append(f"Unknown provider: {self.provider}. Supported: ollama, openai, anthropic, auto")

        return errors


@dataclass
class LLMGenerateNode:
    """
    Represents a <q:llm-generate> tag - generates text using an LLM

    Example:
        <q:llm-generate llm="assistant" prompt="Summarize: {article}" result="summary" />

    Attributes:
        llm_id: ID of the LLM configuration to use
        prompt: Prompt text (can include databinding)
        result_var: Variable name to store the result
        stream: Whether to stream the response (for chat interfaces)
        cache: Whether to cache the result
    """
    llm_id: str
    prompt: str
    result_var: str
    stream: bool = False
    cache: bool = False
    cache_key: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate LLM generate configuration"""
        errors = []

        if not self.llm_id:
            errors.append("llm-generate must have an 'llm' attribute")

        if not self.prompt:
            errors.append("llm-generate must have a 'prompt' attribute")

        if not self.result_var:
            errors.append("llm-generate must have a 'result' attribute")

        return errors


@dataclass
class LLMChatNode:
    """
    Represents a <q:llm-chat> tag - creates a chat interface with an LLM

    Example:
        <q:llm-chat llm="assistant" session="chat_history" />

    Attributes:
        llm_id: ID of the LLM configuration to use
        session_var: Session variable to store chat history
        max_history: Maximum number of messages to keep in history
        show_ui: Whether to render a default chat UI
    """
    llm_id: str
    session_var: str = "chat_history"
    max_history: int = 50
    show_ui: bool = True

    def validate(self) -> List[str]:
        """Validate chat configuration"""
        errors = []

        if not self.llm_id:
            errors.append("llm-chat must have an 'llm' attribute")

        if self.max_history < 1:
            errors.append(f"max_history must be >= 1, got {self.max_history}")

        return errors
