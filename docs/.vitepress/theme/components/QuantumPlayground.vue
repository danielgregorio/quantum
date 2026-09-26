<script setup>
// The playground: the Cookbook's recipes, editable, run by the real
// quantum-framework in the visitor's browser (Pyodide, in a Web Worker:
// public/playground/worker.mjs). The preview is a sandboxed document; its
// links and forms come back here and go to the project's server.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { useData, withBase } from 'vitepress'

const VERSION = __QUANTUM_VERSION__

const TEXT = {
  en: { loading: 'Loading', first: 'The first visit downloads Python and Quantum (about 15 MB); later visits come from the browser cache.',
        example: 'Example', run: 'Run', tests: 'Run tests', reset: 'Reset', preview: 'Preview', testsTab: 'Tests',
        recipe: 'Its Cookbook page', failed: 'Quantum did not load', notRun: 'Press Run to build the project.',
        running: 'Running…', noTests: 'This project has no *.test.q file.', go: 'Go' },
  pt: { loading: 'Carregando', first: 'A primeira visita baixa o Python e o Quantum (cerca de 15 MB); as seguintes vêm do cache do navegador.',
        example: 'Exemplo', run: 'Rodar', tests: 'Rodar testes', reset: 'Desfazer', preview: 'Página', testsTab: 'Testes',
        recipe: 'A receita no Cookbook', failed: 'O Quantum não carregou', notRun: 'Aperte Rodar para montar o projeto.',
        running: 'Rodando…', noTests: 'Este projeto não tem arquivo *.test.q.', go: 'Ir' },
  es: { loading: 'Cargando', first: 'La primera visita descarga Python y Quantum (unos 15 MB); las siguientes vienen de la caché del navegador.',
        example: 'Ejemplo', run: 'Ejecutar', tests: 'Ejecutar pruebas', reset: 'Deshacer', preview: 'Página', testsTab: 'Pruebas',
        recipe: 'La receta en el Recetario', failed: 'Quantum no se cargó', notRun: 'Pulsa Ejecutar para montar el proyecto.',
        running: 'Ejecutando…', noTests: 'Este proyecto no tiene archivos *.test.q.', go: 'Ir' },
  zh: { loading: '正在加载', first: '首次访问会下载 Python 和 Quantum（约 15 MB），之后从浏览器缓存读取。',
        example: '示例', run: '运行', tests: '运行测试', reset: '还原', preview: '页面', testsTab: '测试',
        recipe: '实用示例中的这一篇', failed: 'Quantum 加载失败', notRun: '点击“运行”来构建项目。',
        running: '正在运行…', noTests: '这个项目没有 *.test.q 文件。', go: '前往' },
}
const { lang } = useData()
const t = computed(() => TEXT[(lang.value || 'en').slice(0, 2)] || TEXT.en)

const topics = ref([])
const recipe = shallowRef(null)
const files = ref({})
const active = ref('')
const status = ref('')
const failure = ref('')
const ready = ref(false)
const busy = ref(false)
const view = ref('preview')
const path = ref('/')
const address = ref('/')
const pageStatus = ref(0)
const report = ref('')
const reportCode = ref(null)
const frame = ref(null)
const srcdoc = ref('')

let worker = null
let nextId = 0
const pending = new Map()

function call(type, payload = {}) {
  const id = ++nextId
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject })
    worker.postMessage({ id, type, ...payload })
  })
}

const fileNames = computed(() => Object.keys(files.value).sort((a, b) => rank(a) - rank(b) || a.localeCompare(b)))
function rank(name) {
  if (name.startsWith('components/') && !name.endsWith('.test.q')) return 0
  if (name.endsWith('.test.q')) return 1
  if (name.startsWith('migrations/')) return 2
  return 3
}

function choose(id) {
  for (const topic of topics.value) for (const r of topic.recipes) {
    if (r.id !== id) continue
    recipe.value = r
    files.value = { ...r.files }
    active.value = fileNames.value[0]
    view.value = r.view
    report.value = ''
    reportCode.value = null
    srcdoc.value = ''
    if (location.hash.slice(1) !== id) history.replaceState(null, '', '#' + id)
    if (ready.value) run()
    return
  }
}

function reset() {
  if (recipe.value) choose(recipe.value.id)
}

async function run() {
  if (!ready.value || busy.value) return
  busy.value = true
  failure.value = ''
  try {
    const built = await call('load', { files: { ...files.value } })
    if (built.error) {
      showError(built.error)
      return
    }
    if (view.value === 'tests') await runTests(true)
    await go('GET', recipe.value.start)
  } finally {
    busy.value = false
  }
}

async function runTests(inside = false) {
  if (!ready.value || (busy.value && !inside)) return
  if (!Object.keys(files.value).some(n => n.endsWith('.test.q'))) {
    report.value = t.value.noTests
    reportCode.value = null
    view.value = 'tests'
    return
  }
  if (!inside) busy.value = true
  view.value = 'tests'
  report.value = t.value.running
  try {
    if (!inside) {
      const built = await call('load', { files: { ...files.value } })
      if (built.error) {
        report.value = built.error
        reportCode.value = 1
        return
      }
    }
    const result = await call('test')
    report.value = result.report
    reportCode.value = result.code
  } finally {
    if (!inside) busy.value = false
  }
  if (!inside) await go('GET', path.value)     // the tests rebuilt the world; the preview follows
}

async function go(method, target, form) {
  const answer = await call('request', { method, path: target, form })
  path.value = answer.path
  address.value = answer.path
  pageStatus.value = answer.status
  if (answer.error) {
    showError(answer.error)
    return
  }
  srcdoc.value = answer.content_type && !answer.content_type.includes('html')
    ? `<pre style="white-space:pre-wrap;font:13px monospace">${escape(answer.html)}</pre>`
    : withNavigation(answer.html)
}

function showError(text) {
  srcdoc.value = `<pre style="white-space:pre-wrap;color:#b91c1c;font:13px monospace;padding:12px">${escape(text)}</pre>`
  pageStatus.value = 0
  view.value = 'preview'
}

function escape(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// The preview has no server behind it: its links and forms post back to us.
const NAVIGATION = `<script>(function () {
  function send(message) { parent.postMessage(Object.assign({ quantumPlayground: true }, message), '*') }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]')
    if (!a) return
    var href = a.getAttribute('href')
    if (/^#/.test(href)) return
    e.preventDefault()
    if (/^[a-z][a-z0-9+.-]*:/i.test(href)) { window.open(href, '_blank', 'noopener'); return }
    send({ method: 'GET', href: href })
  }, true)
  document.addEventListener('submit', function (e) {
    var form = e.target
    e.preventDefault()
    var data = {}
    new FormData(form, e.submitter).forEach(function (value, key) {
      if (typeof value !== 'string') return
      data[key] = key in data ? [].concat(data[key], value) : value
    })
    send({ method: (form.getAttribute('method') || 'GET').toUpperCase(), href: form.getAttribute('action') || '', form: data })
  }, true)
})()<\/script>`

function withNavigation(html) {
  return /<\/body>/i.test(html) ? html.replace(/<\/body>/i, NAVIGATION + '</body>') : html + NAVIGATION
}

function onPreviewMessage(event) {
  if (!frame.value || event.source !== frame.value.contentWindow) return
  const message = event.data || {}
  if (!message.quantumPlayground || busy.value) return
  const url = new URL(message.href || path.value, 'http://playground' + path.value)
  let target = url.pathname + url.search
  let form = message.form || null
  if (message.method === 'GET' && form) {
    const query = new URLSearchParams()
    for (const [k, v] of Object.entries(form)) for (const one of [].concat(v)) query.append(k, one)
    target = url.pathname + '?' + query.toString()
    form = null
  }
  busy.value = true
  go(message.method, target, form).finally(() => { busy.value = false })
}

function onAddress() {
  if (busy.value || !ready.value) return
  busy.value = true
  go('GET', address.value.startsWith('/') ? address.value : '/' + address.value).finally(() => { busy.value = false })
}

function onKey(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault()
    run()
  }
  if (event.key === 'Tab') {                      // two spaces, as the recipes are indented
    event.preventDefault()
    const el = event.target
    const { selectionStart: s, selectionEnd: e } = el
    files.value[active.value] = el.value.slice(0, s) + '  ' + el.value.slice(e)
    nextTick(() => { el.selectionStart = el.selectionEnd = s + 2 })
  }
}

onMounted(async () => {
  window.addEventListener('message', onPreviewMessage)
  const data = await (await fetch(withBase('/playground/recipes.json'))).json()
  topics.value = data.topics
  const wanted = location.hash.slice(1)
  const all = data.topics.flatMap(topic => topic.recipes)
  choose(all.some(r => r.id === wanted) ? wanted : all[0].id)

  worker = new Worker(withBase('/playground/worker.mjs'), { type: 'module' })
  worker.onmessage = ({ data: message }) => {
    if (message.status) {
      status.value = message.status
      return
    }
    const waiting = pending.get(message.id)
    if (!waiting) return
    pending.delete(message.id)
    message.error ? waiting.reject(new Error(message.error)) : waiting.resolve(message.result)
  }
  try {
    await call('boot', { version: VERSION })
    ready.value = true
    run()
  } catch (e) {
    failure.value = String(e.message || e)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onPreviewMessage)
  if (worker) worker.terminate()
})
</script>

<template>
  <div class="qp">
    <div class="qp-bar">
      <label class="qp-pick">
        <span>{{ t.example }}</span>
        <select :value="recipe && recipe.id" @change="choose($event.target.value)">
          <optgroup v-for="topic in topics" :key="topic.topic" :label="topic.title">
            <option v-for="r in topic.recipes" :key="r.id" :value="r.id">{{ r.title }}</option>
          </optgroup>
        </select>
      </label>
      <button class="qp-run" :disabled="!ready || busy" @click="run">{{ t.run }} ▶</button>
      <button :disabled="!ready || busy" @click="runTests()">{{ t.tests }}</button>
      <button :disabled="busy" @click="reset">{{ t.reset }}</button>
      <span class="qp-version">quantum-framework {{ VERSION }}</span>
    </div>
    <p v-if="recipe" class="qp-about">
      {{ recipe.description }}
      <a :href="withBase(recipe.cookbook)">{{ t.recipe }} →</a>
    </p>

    <div class="qp-main">
      <div class="qp-editor">
        <div class="qp-tabs" role="tablist">
          <button v-for="name in fileNames" :key="name" role="tab" :aria-selected="name === active"
                  :class="{ on: name === active }" @click="active = name">{{ name }}</button>
        </div>
        <textarea v-if="active" v-model="files[active]" spellcheck="false" autocapitalize="off"
                  autocomplete="off" :aria-label="active" @keydown="onKey" />
      </div>

      <div class="qp-output">
        <div class="qp-tabs" role="tablist">
          <button role="tab" :aria-selected="view === 'preview'" :class="{ on: view === 'preview' }"
                  @click="view = 'preview'">{{ t.preview }}</button>
          <button role="tab" :aria-selected="view === 'tests'" :class="{ on: view === 'tests' }"
                  @click="view = 'tests'">{{ t.testsTab }}
            <span v-if="reportCode !== null" :class="reportCode === 0 ? 'qp-pass' : 'qp-fail'">●</span>
          </button>
        </div>
        <div v-if="!ready" class="qp-loading">
          <template v-if="failure"><strong>{{ t.failed }}:</strong> {{ failure }}</template>
          <template v-else>
            <p><strong>{{ t.loading }}…</strong> {{ status }}</p>
            <p>{{ t.first }}</p>
          </template>
        </div>
        <template v-else>
          <form v-show="view === 'preview'" class="qp-address" @submit.prevent="onAddress">
            <span :class="['qp-status', pageStatus >= 400 || pageStatus === 0 ? 'bad' : '']">{{ pageStatus || '—' }}</span>
            <input v-model="address" aria-label="URL" />
            <button :disabled="busy">{{ t.go }}</button>
          </form>
          <iframe v-show="view === 'preview'" ref="frame" class="qp-frame" title="Preview"
                  sandbox="allow-scripts allow-forms allow-modals allow-popups" :srcdoc="srcdoc || `<p style='font:14px sans-serif;color:#666;padding:12px'>${t.notRun}</p>`" />
          <pre v-show="view === 'tests'" class="qp-report">{{ report || t.notRun }}</pre>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.qp { display: flex; flex-direction: column; gap: 12px; }
.qp-bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.qp-pick { display: flex; gap: 8px; align-items: center; flex: 1 1 280px; }
.qp-pick select { flex: 1; min-width: 0; }
.qp select, .qp button, .qp input {
  border: 1px solid var(--vp-c-divider); border-radius: 6px; padding: 6px 10px;
  background: var(--vp-c-bg-soft); color: var(--vp-c-text-1); font-size: 14px;
}
.qp button { cursor: pointer; }
.qp button:disabled { opacity: .5; cursor: default; }
.qp .qp-run { background: var(--vp-c-brand-1); border-color: var(--vp-c-brand-1); color: var(--vp-c-white); font-weight: 600; }
.qp-version { margin-left: auto; font-size: 12px; color: var(--vp-c-text-2); }
.qp-about { margin: 0; font-size: 14px; color: var(--vp-c-text-2); }
.qp-main { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; min-height: 560px; }
@media (max-width: 900px) { .qp-main { grid-template-columns: 1fr; } }
.qp-editor, .qp-output { display: flex; flex-direction: column; min-width: 0;
  border: 1px solid var(--vp-c-divider); border-radius: 8px; overflow: hidden; }
.qp-tabs { display: flex; overflow-x: auto; background: var(--vp-c-bg-soft); border-bottom: 1px solid var(--vp-c-divider); }
.qp .qp-tabs button { border: 0; border-radius: 0; background: transparent; white-space: nowrap; font-size: 13px;
  color: var(--vp-c-text-2); padding: 8px 12px; }
.qp .qp-tabs button.on { color: var(--vp-c-text-1); box-shadow: inset 0 -2px var(--vp-c-brand-1); }
.qp-editor textarea { flex: 1; min-height: 520px; border: 0; resize: none; padding: 12px; outline: none;
  font: 13px/1.5 var(--vp-font-family-mono); background: var(--vp-c-bg); color: var(--vp-c-text-1); tab-size: 2; }
.qp-address { display: flex; gap: 6px; padding: 6px; border-bottom: 1px solid var(--vp-c-divider); align-items: center; }
.qp-address input { flex: 1; min-width: 0; font-family: var(--vp-font-family-mono); }
.qp-status { font: 12px var(--vp-font-family-mono); color: #16a34a; min-width: 2.5em; text-align: center; }
.qp-status.bad { color: #dc2626; }
.qp-frame { flex: 1; width: 100%; min-height: 480px; border: 0; background: #fff; }
.qp-report { flex: 1; margin: 0; padding: 12px; overflow: auto; font: 13px/1.5 var(--vp-font-family-mono);
  background: var(--vp-c-bg); white-space: pre-wrap; }
.qp-loading { padding: 16px; font-size: 14px; color: var(--vp-c-text-2); }
.qp-pass { color: #16a34a; }
.qp-fail { color: #dc2626; }
</style>
