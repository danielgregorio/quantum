# Quantum Framework - Cross-Platform Benchmark Suite

Benchmarks comparativos entre Quantum e outras tecnologias web.

## Tecnologias Testadas

| Tecnologia | Versão | Tipo |
|------------|--------|------|
| **Quantum** | 1.0 | Framework declarativo (Python) |
| Python puro | 3.12 | Linguagem |
| Flask | 3.0 | Microframework Python |
| Django | 5.0 | Framework Python |
| PHP | 8.3 | Linguagem |
| Laravel | 11.x | Framework PHP |
| Ruby | 3.3 | Linguagem |
| Rails | 7.x | Framework Ruby |
| Perl CGI | 5.38 | Linguagem |
| Node.js | 20.x | Runtime JavaScript |
| Express | 4.x | Framework Node.js |
| Java | 21 | Linguagem |
| Spring Boot | 3.x | Framework Java |

## Categorias de Benchmark

### 1. Micro-benchmarks (Operações isoladas)
- Avaliação de expressões
- Manipulação de variáveis
- Loops (1000, 10000, 100000 iterações)
- Condicionais
- String interpolation
- JSON parse/serialize

### 2. HTTP Benchmarks (Requisições web)
- Hello World (resposta mínima)
- JSON response
- Template rendering
- Database query (SQLite)

### 3. Real-world Scenarios
- CRUD simples
- Lista paginada
- Formulário com validação

## Como Executar

```bash
# Todos os benchmarks
python benchmarks/cross_platform/run_all.py

# Apenas micro-benchmarks
python benchmarks/cross_platform/bench_micro.py

# Apenas HTTP (requer instalação das outras tecnologias)
python benchmarks/cross_platform/bench_http.py
```

## Resultados

Os resultados são salvos em `benchmarks/results/cross_platform_YYYYMMDD_HHMMSS.json`
