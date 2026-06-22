// Monaco loader for Vite.
// Loaded ONLY when the workbench route is entered.

import * as monaco from 'monaco-editor/esm/vs/editor/editor.api'

import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import JsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'
import CssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker'
import HtmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker'
import TsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker'

export function ensureMonacoWorkers() {
  // Ensure it's set once. Monaco reads global MonacoEnvironment.
  if (globalThis.MonacoEnvironment?.getWorker) return

  globalThis.MonacoEnvironment = {
    getWorker(_moduleId, label) {
      if (label === 'json') return new JsonWorker()
      if (label === 'css' || label === 'scss' || label === 'less') return new CssWorker()
      if (label === 'html' || label === 'handlebars' || label === 'razor') return new HtmlWorker()
      if (label === 'typescript' || label === 'javascript') return new TsWorker()
      return new EditorWorker()
    },
  }
}

export async function loadMonaco() {
  ensureMonacoWorkers()
  return monaco
}
