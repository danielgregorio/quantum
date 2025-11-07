# Quantum MXML - Automated Testing System

## 📋 Overview

Sistema completo de validação automatizada para demos compilados com Quantum MXML.

### Componentes:

1. **Health Check System** - Sistema de monitoramento integrado em cada demo
2. **Test Runner** - Script Python para testar todos os demos automaticamente
3. **Auto-Recompile** - Recompilação automática de demos com falhas

---

## 🏥 Health Check System

### Como Funciona:

Cada demo compilado agora inclui um sistema de health check que:

- Monitora erros JavaScript
- Captura warnings do console
- Rastreia status de carregamento
- Expõe status via `window.__quantumHealth`

### Estrutura do Health Check:

```javascript
window.__quantumHealth = {
  status: 'ready' | 'initializing' | 'error',
  timestamp: 1234567890,
  readyTimestamp: 1234567900,
  app: 'App',
  errors: [
    {
      message: 'Error message',
      timestamp: 1234567895,
      filename: 'app.js',
      lineno: 123,
      colno: 45
    }
  ],
  warnings: [
    {
      message: 'Warning message',
      timestamp: 1234567896
    }
  ]
}
```

### Status Values:

- `initializing` - Aplicação está carregando
- `ready` - Aplicação carregou com sucesso
- `error` - Aplicação teve erros

### Console Log:

Quando a aplicação carrega com sucesso:
```
[QUANTUM-HEALTH] Application loaded successfully
```

---

## 🧪 Test Runner

### Instalação:

```bash
# Instalar Selenium
pip install selenium

# Baixar ChromeDriver
# https://chromedriver.chromium.org/
# Adicionar ao PATH do sistema
```

### Uso Básico:

```bash
# Testar todos os demos
python test_demos.py

# Testar e recompilar demos com falhas
python test_demos.py --recompile

# Modo verbose (mostrar logs detalhados)
python test_demos.py --verbose

# URL customizada
python test_demos.py --url http://localhost:8080
```

### O que o Test Runner faz:

1. **Carrega cada demo** no Chrome headless
2. **Aguarda health check** inicializar
3. **Verifica status** da aplicação
4. **Captura erros** JavaScript e warnings
5. **Mede tempo de carregamento**
6. **Gera relatório** JSON

### Saída do Test Runner:

```
======================================================================
QUANTUM MXML DEMO TEST SUITE
======================================================================

Testing 11 demos at http://localhost:8547
----------------------------------------------------------------------

[1/11] Testing: Hello World
  [PASS] Application loaded successfully in 0.23s

[2/11] Testing: FASE 1 MVP Demo
  [PASS] Application loaded successfully in 0.45s

[3/11] Testing: E-Commerce Admin Dashboard
  [PASS] Application loaded successfully in 0.67s

...

======================================================================
TEST SUMMARY
======================================================================
Total: 11
Passed: 11 (100.0%)
Failed: 0 (0.0%)
Errors: 0 (0.0%)
======================================================================

Test report saved to: test_report.json
```

### Relatório JSON:

```json
{
  "timestamp": 1234567890,
  "base_url": "http://localhost:8547",
  "total": 11,
  "passed": 11,
  "failed": 0,
  "errors": 0,
  "results": [
    {
      "name": "Hello World",
      "path": "hello",
      "url": "http://localhost:8547/hello/",
      "status": "pass",
      "health": {
        "status": "ready",
        "errors": [],
        "warnings": []
      },
      "load_time": 0.23,
      "message": "Application loaded successfully in 0.23s"
    }
  ]
}
```

---

## 🔄 Auto-Recompile

### Uso:

```bash
# Recompilar todos os demos
python recompile_all.py

# Testar e recompilar apenas demos com falhas
python test_demos.py --recompile
```

### O que faz:

1. Identifica demos com falhas
2. Recompila MXML source
3. Copia arquivos atualizados para `docs/`
4. Reporta sucesso/falha

---

## 🚀 Workflow Recomendado

### 1. Desenvolvimento Normal:

```bash
# Modificar compilador (as4_parser.py, codegen.py, etc.)

# Recompilar um demo específico
python quantum-mxml build examples/ecommerce-admin.mxml
cp dist/app.js docs/ecommerce-admin/

# Testar manualmente no browser
# http://localhost:8547/ecommerce-admin/
```

### 2. Teste Automatizado:

```bash
# Após mudanças no compilador, testar TODOS os demos
python test_demos.py

# Se algum demo falhar, verificar erros no relatório
cat test_report.json
```

### 3. Recompile em Massa:

```bash
# Após fix no compilador, recompilar todos
python recompile_all.py

# Testar novamente
python test_demos.py
```

### 4. Integração Contínua:

```bash
# Adicionar ao CI/CD pipeline:
python test_demos.py
if [ $? -ne 0 ]; then
  echo "Tests failed!"
  exit 1
fi
```

---

## 📊 Métricas Capturadas

### Por Demo:

- ✅ Status (pass/fail/error)
- ⏱️ Tempo de carregamento
- 🐛 Erros JavaScript
- ⚠️ Warnings
- 📝 Stack traces completos

### Agregadas:

- Taxa de sucesso geral
- Tempo médio de carregamento
- Demos mais problemáticos
- Erros mais comuns

---

## 🔍 Debugging

### Ver Health Status no Browser:

```javascript
// Abrir console do browser (F12)
console.log(window.__quantumHealth);

// Output:
// {
//   status: 'ready',
//   errors: [],
//   warnings: [],
//   app: 'App'
// }
```

### Forçar Erro para Testar:

```javascript
// No console do browser:
throw new Error('Test error');

// Health status será atualizado:
window.__quantumHealth.status === 'error'
window.__quantumHealth.errors.length > 0
```

---

## 📂 Arquivos Criados

### Compilador:

- `compiler/as4_parser.py` - ✅ Fixed: Brace counting for else blocks
- `compiler/codegen.py` - ✅ Added: Health check registration
- `compiler/runtime/reactive-runtime.js` - ✅ Added: `registerHealthCheck()` method
- `quantum-mxml` - ✅ Fixed: Removed emojis causing encoding errors

### Testing:

- `test_demos.py` - Test runner automatizado (Selenium)
- `recompile_all.py` - Recompilador em massa
- `test_parser_bug.py` - Teste específico para bug de else blocks
- `BUG_REPORT_ELSE_BLOCKS.md` - Documentação do bug corrigido

### Reports:

- `test_report.json` - Relatório JSON dos testes (gerado automaticamente)

---

## ✅ Bugs Corrigidos

### 1. Else Blocks Removidos (CRÍTICO)

**Problema:** Compilador removia todos os blocos `else` do JavaScript gerado.

**Root Cause:** Regex `(.*?)` (non-greedy) parava no primeiro `}`, perdendo o resto da função.

**Fix:** Implementado brace counting para encontrar fechamento correto de função.

**Files:**
- `compiler/as4_parser.py` linha 168-233

**Status:** ✅ FIXED - Testado e validado

### 2. Emojis Causando UnicodeEncodeError

**Problema:** Emojis em prints causavam crash no Windows.

**Fix:** Substituídos por texto simples:
- `🔨` → `Building`
- `✅` → `[SUCCESS]`
- `❌` → `[ERROR]`

**Files:**
- `quantum-mxml` linhas 30, 91, 104, etc.

**Status:** ✅ FIXED

---

## 🎯 Próximos Passos

### Melhorias Planejadas:

1. **Performance Testing**
   - Medir tempo de render
   - Detectar memory leaks
   - Profile JavaScript execution

2. **Visual Regression**
   - Screenshot comparisons
   - Detect UI changes
   - Automated visual diffing

3. **Integration Tests**
   - Test user interactions
   - Test API calls
   - Test state management

4. **Coverage Reports**
   - Code coverage for compiler
   - Test coverage for demos
   - Feature coverage matrix

---

## 📞 Suporte

Se encontrar problemas:

1. Verificar logs do test runner
2. Verificar `test_report.json`
3. Abrir demo no browser e verificar console
4. Verificar `window.__quantumHealth`
5. Reportar issue com logs completos

---

**Last Updated:** 2025-01-07
**Version:** 1.0.0
