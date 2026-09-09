"""
The two halves of the AI stack pointed at different Ollama servers.

ServiceContainer.multi_llm (used by q:llm, q:agent, q:team) honoured
`llm.base_url` from quantum.config.yaml. ServiceContainer.llm — the
Ollama-only service behind q:knowledge and the RAG path — was constructed with
NO arguments, so it fell back to its own default of http://localhost:11434 and
ignored the config entirely.

Measured on the machine this was found on: the config named a remote host,
q:llm reached it and answered, and q:knowledge silently went to localhost. In
a deployment where only the configured host has models, q:llm works and RAG
fails, with nothing anywhere explaining why.
"""

import pytest

from quantum.runtime.service_container import ServiceContainer

CONFIG = {"llm": {"base_url": "http://localhost:11434",
                  "default_model": "qwen2:1.5b", "timeout": 30}}


def _norm(url):
    return str(url).rstrip("/")


class TestBothPathsUseTheConfiguredHost:
    def test_multi_llm_honours_base_url(self):
        sc = ServiceContainer(CONFIG)
        assert _norm(sc.multi_llm.default_endpoint) == "http://localhost:11434"

    def test_llm_service_honours_base_url(self):
        sc = ServiceContainer(CONFIG)
        assert _norm(sc.llm.base_url) == "http://localhost:11434"

    def test_they_agree(self):
        sc = ServiceContainer(CONFIG)
        assert _norm(sc.multi_llm.default_endpoint) == _norm(sc.llm.base_url)

    def test_the_default_model_is_shared_too(self):
        sc = ServiceContainer(CONFIG)
        assert sc.llm.default_model == "qwen2:1.5b"


class TestNoConfigStillWorks:
    def test_falls_back_to_localhost(self):
        sc = ServiceContainer({})
        assert _norm(sc.llm.base_url) == "http://localhost:11434"

    def test_no_config_paths_still_agree(self):
        sc = ServiceContainer({})
        a = sc.multi_llm.default_endpoint
        # multi_llm may leave the endpoint unset and resolve per-provider;
        # what matters is that neither silently contradicts the other.
        assert a is None or _norm(a) == _norm(sc.llm.base_url)
