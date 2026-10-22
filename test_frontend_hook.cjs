const fs = require('fs');
const vm = require('vm');
const ts = require('typescript');
const sourcePath = process.argv[2];
const source = fs.readFileSync(sourcePath, 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }
}).outputText;

async function observe(payload) {
  const values = [];
  let counter = 0;
  const react = {
    useState(initial) {
      const index = values.length;
      values.push(initial);
      return [initial, next => {
        values[index] = typeof next === 'function' ? next(values[index]) : next;
      }];
    },
    useCallback: fn => fn,
  };
  const module = { exports: {} };
  const context = {
    exports: module.exports,
    module,
    require(name) {
      if (name === 'react') return react;
      if (name === 'uuid') return {v4: () => `synthetic-${++counter}`};
      throw new Error(`Unexpected dependency: ${name}`);
    },
    fetch: async () => ({ ok: true, status: 200, json: async () => payload }),
    console: { error() {}, log() {} },
  };
  vm.runInNewContext(compiled, context, {filename:sourcePath, timeout:3000});
  const hook = module.exports.useAgentChat('synthetic-session');
  await hook.sendMessage('synthetic message');
  return JSON.parse(JSON.stringify(values[0][1].state));
}

(async () => {
  const blocked = await observe({status:'success',plugin_used:'finance_assistant',reply:'blocked',is_safe:false,risk_reason:'synthetic block'});
  const allowed = await observe({status:'success',plugin_used:'finance_assistant',reply:'allowed',is_safe:true,risk_reason:null});
  process.stdout.write(JSON.stringify({blocked,allowed}));
})().catch(error => { process.stderr.write(error.stack); process.exitCode=1; });
