// The playground's engine: Pyodide, the real quantum-framework, and bridge.py.
//
// The browser runs it in a Web Worker (worker.mjs); scripts/check-playground.mjs
// runs it in Node, with the repository's own quantum/ package in place of the
// one from PyPI.

export const PYODIDE_VERSION = '314.0.7'
export const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

// Pyodide's own builds of what Quantum imports (and what the recipes use:
// bcrypt for the login recipes). Flask and sqlparse are pure Python, from PyPI.
const PYODIDE_PACKAGES = ['micropip', 'pyyaml', 'requests', 'bcrypt']
const FROM_PYPI = ['flask', 'sqlparse']

// boot({ loadPyodide, bridgeSource, installQuantum }) -> engine
//   installQuantum(py, micropip): puts quantum-framework on the path. The site
//   installs the version it documents from PyPI; the test copies quantum/.
export async function boot({ loadPyodide, indexURL, bridgeSource, installQuantum, onStatus = () => {} }) {
  onStatus('Loading Python')
  const py = await loadPyodide(indexURL ? { indexURL } : {})
  onStatus('Loading packages')
  await py.loadPackage(PYODIDE_PACKAGES, { messageCallback: () => {} })
  const micropip = py.pyimport('micropip')
  await micropip.install(FROM_PYPI)
  onStatus('Loading Quantum')
  await installQuantum(py, micropip)
  py.FS.mkdirTree('/playground')
  py.FS.writeFile('/playground/bridge.py', bridgeSource)
  py.runPython(`
import logging, sys
sys.path.insert(0, '/playground')
logging.disable(logging.WARNING)       # the server's startup notes are not the visitor's business
import bridge
`)
  const bridge = py.pyimport('bridge').playground
  const js = value => value.toJs({ dict_converter: Object.fromEntries, create_pyproxies: false })
  const version = py.runPython('import importlib.metadata as m\n' +
    'try:\n  v = m.version("quantum-framework")\nexcept Exception:\n  v = "source"\nv')
  onStatus('Ready')
  return {
    version,
    load: files => js(bridge.load(py.toPy(files))),
    request: (method, path, form) => js(bridge.request(method, path, form ? py.toPy(form) : null)),
    test: () => js(bridge.test()),
  }
}
