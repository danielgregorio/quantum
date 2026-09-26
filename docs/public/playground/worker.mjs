// The playground's Web Worker: Quantum runs here, off the page's thread.
// Messages in: { id, type: 'boot', version } | { id, type: 'load', files }
//            | { id, type: 'request', method, path, form } | { id, type: 'test' }
// Messages out: { id, result } | { id, error } | { status } while booting.

import { boot, PYODIDE_URL } from './core.mjs'

let engine = null

async function start(version) {
  const { loadPyodide } = await import(PYODIDE_URL + 'pyodide.mjs')
  const bridgeSource = await (await fetch(new URL('./bridge.py', import.meta.url))).text()
  engine = await boot({
    loadPyodide,
    indexURL: PYODIDE_URL,
    bridgeSource,
    // The version the site documents, from PyPI; its own dependencies are
    // the ones boot() loaded (the rest serve the console and the server).
    installQuantum: (py, micropip) => micropip.install(`quantum-framework==${version}`, { deps: false }),
    onStatus: status => self.postMessage({ status }),
  })
  return { version: engine.version }
}

self.onmessage = async ({ data }) => {
  const { id, type } = data
  try {
    let result
    if (type === 'boot') result = await start(data.version)
    else if (!engine) throw new Error('Quantum is still loading')
    else if (type === 'load') result = engine.load(data.files)
    else if (type === 'request') result = engine.request(data.method, data.path, data.form)
    else if (type === 'test') result = engine.test()
    else throw new Error(`unknown message: ${type}`)
    self.postMessage({ id, result })
  } catch (e) {
    self.postMessage({ id, error: String(e && e.message || e) })
  }
}
