"""A stand-in for an Ollama server, over real HTTP, for tests that must not need one.

It answers the endpoints Quantum calls — /api/chat (whole or streamed),
/api/generate, /api/embed, /api/tags, /api/pull — and keeps every request it
received. Embeddings are a bag of words hashed into a small vector, so texts
that share words are near each other and retrieval behaves like retrieval.

    with FakeOllama() as ollama:
        ollama.reply = 'Hello [1]'                  # or a function of the messages
        ollama.fail['/api/embed'] = (500, 'boom')   # an endpoint that fails
        ... QUANTUM_LLM_BASE_URL=ollama.url ...
"""

import hashlib
import json
import math
import re
import threading
import time

from werkzeug.serving import make_server
from werkzeug.wrappers import Request, Response

DIMENSIONS = 1024
STOPWORDS = {'the', 'and', 'how', 'what', 'does', 'into', 'from', 'with', 'for', 'are', 'between'}


def embed(text):
    vector = [0.0] * DIMENSIONS
    for word in re.findall(r'[a-z0-9]{3,}', text.lower()):
        if word in STOPWORDS:
            continue
        vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIMENSIONS] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class FakeOllama:
    def __init__(self):
        self.reply = 'fake answer'
        self.models = ['phi3', 'nomic-embed-text']
        self.fail = {}                   # path -> (status, body)
        self.delay = 0.0                 # seconds before answering
        self.embed_count = None          # force a wrong number of embeddings
        self.received = []               # (path, json body)
        self.server = make_server('127.0.0.1', 0, self.app, threaded=True)
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()

    def paths(self):
        return [path for path, _ in self.received]

    def _text(self, messages):
        return self.reply(messages) if callable(self.reply) else self.reply

    @Request.application
    def app(self, request):
        body = json.loads(request.data) if request.data else {}
        self.received.append((request.path, body))
        if self.delay:
            time.sleep(self.delay)
        if request.path in self.fail:
            status, text = self.fail[request.path]
            return Response(text, status=status)
        model = body.get('model', 'phi3')

        if request.path == '/api/chat':
            text = self._text(body['messages'])
            if body.get('stream'):
                def pieces():
                    for word in re.findall(r'\S+\s*', text):
                        yield json.dumps({'message': {'content': word}, 'done': False}) + '\n'
                    yield json.dumps({'message': {'content': ''}, 'done': True}) + '\n'
                return Response(pieces(), content_type='application/x-ndjson')
            return self._json({'model': model, 'message': {'role': 'assistant', 'content': text},
                               'done': True, 'prompt_eval_count': 7, 'eval_count': 3})
        if request.path == '/api/generate':
            text = self._text([{'role': 'user', 'content': body.get('prompt', '')}])
            return self._json({'model': model, 'response': text, 'done': True, 'eval_count': 3})
        if request.path == '/api/embed':
            texts = body['input'] if isinstance(body['input'], list) else [body['input']]
            vectors = [embed(t) for t in texts][:self.embed_count]
            return self._json({'model': model, 'embeddings': vectors})
        if request.path == '/api/tags':
            return self._json({'models': [{'name': m} for m in self.models]})
        if request.path == '/api/pull':
            return self._json({'status': 'success'})
        return Response('not found', status=404)

    @staticmethod
    def _json(data):
        return Response(json.dumps(data), content_type='application/json')
