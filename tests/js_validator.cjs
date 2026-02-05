/**
 * JS Syntax Validator for Quantum Game Engine E2E Tests
 *
 * Receives HTML via stdin, extracts the <script> block,
 * and validates JS syntax using vm.Script().
 *
 * Exit code 0 = valid JS syntax
 * Exit code 1 = syntax error (details on stderr)
 */

const vm = require('vm');

let input = '';

process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});

process.stdin.on('end', () => {
  // Extract JS from <script> tags (skip CDN script tags with src)
  const scriptRegex = /<script>([^]*?)<\/script>/gi;
  let match;
  let jsCode = '';

  while ((match = scriptRegex.exec(input)) !== null) {
    jsCode += match[1] + '\n';
  }

  if (!jsCode.trim()) {
    process.stderr.write('No inline <script> content found in HTML\n');
    process.exit(1);
  }

  try {
    // vm.Script compiles the code, checking for syntax errors
    // It does NOT execute the code
    new vm.Script(jsCode, { filename: 'game.js' });
    process.exit(0);
  } catch (err) {
    process.stderr.write(`JS Syntax Error: ${err.message}\n`);
    if (err.stack) {
      // Extract the relevant line info
      const lines = err.stack.split('\n').slice(0, 5);
      process.stderr.write(lines.join('\n') + '\n');
    }
    process.exit(1);
  }
});
