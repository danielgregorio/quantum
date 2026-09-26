// Every playground example, run in Pyodide as the browser runs it:
// core.mjs boots Pyodide and bridge.py, with this repository's quantum/
// in place of the release on PyPI. For each recipe in recipes.json: it builds,
// its first page answers, and its own tests pass. CI runs it after the docs build.
//
//   npm ci && node scripts/check-playground.mjs

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { loadPyodide } from 'pyodide'

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const HERE = path.join(REPO, 'docs', 'public', 'playground')
const { boot, PYODIDE_VERSION } = await import(pathToFileURL(path.join(HERE, 'core.mjs')))

const installed = JSON.parse(fs.readFileSync(path.join(REPO, 'node_modules', 'pyodide', 'package.json'), 'utf8')).version
if (installed !== PYODIDE_VERSION) {
  console.error(`core.mjs loads Pyodide ${PYODIDE_VERSION} in the browser, package.json installs ${installed}`)
  process.exit(1)
}

function copyInto(py, src, dst) {
  py.FS.mkdirTree(dst)
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    if (e.name === '__pycache__') continue
    const s = path.join(src, e.name)
    if (e.isDirectory()) copyInto(py, s, `${dst}/${e.name}`)
    else py.FS.writeFile(`${dst}/${e.name}`, fs.readFileSync(s))
  }
}

const engine = await boot({
  loadPyodide,
  bridgeSource: fs.readFileSync(path.join(HERE, 'bridge.py'), 'utf8'),
  installQuantum: async py => {
    const site = py.runPython('import sysconfig; sysconfig.get_paths()["purelib"]')
    copyInto(py, path.join(REPO, 'quantum'), `${site}/quantum`)
  },
})

const recipes = JSON.parse(fs.readFileSync(path.join(HERE, 'recipes.json'), 'utf8'))
let failures = 0
for (const topic of recipes.topics) {
  for (const recipe of topic.recipes) {
    const built = engine.load(recipe.files)
    let problem = built.error
    if (!problem) {
      const page = engine.request('GET', recipe.start, null)
      const ok = recipe.view === 'tests' ? [200, 404] : [200]
      if (!ok.includes(page.status)) problem = `${recipe.start} answered ${page.status}`
    }
    if (!problem) {
      const tests = engine.test()
      if (tests.code !== 0) problem = `its tests failed:\n${tests.report}`
    }
    console.log(`${problem ? 'FAIL' : 'ok  '}  ${recipe.id}${problem ? `\n      ${problem}` : ''}`)
    if (problem) failures++
  }
}
console.log(failures ? `${failures} failed` : `every example runs in Pyodide ${PYODIDE_VERSION}`)
process.exit(failures ? 1 : 0)
