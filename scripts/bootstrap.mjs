import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const rootDir = path.join(fileURLToPath(new URL('.', import.meta.url)), '..');
const isWindows = process.platform === 'win32';

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: 'inherit',
    cwd: rootDir,
    shell: false,
    ...options
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function ensurePythonEnv() {
  const venvDir = path.join(rootDir, '.venv');
  if (existsSync(venvDir)) {
    return;
  }
  const script = path.join(rootDir, 'scripts', isWindows ? 'setup_python_env.ps1' : 'setup_python_env.sh');
  if (isWindows) {
    run('powershell.exe', ['-ExecutionPolicy', 'Bypass', '-File', script]);
  } else {
    run('bash', [script]);
  }
}

function ensureFrontendDeps() {
  const nodeModulesDir = path.join(rootDir, 'frontend', 'node_modules');
  if (existsSync(nodeModulesDir)) {
    return;
  }
  run('npm', ['install'], { cwd: path.join(rootDir, 'frontend') });
}

function ensureHusky() {
  run('npx', ['--no-install', 'husky', 'install']);
}

if (!process.env.FM_BOOTSTRAP_SKIP) {
  ensurePythonEnv();
  ensureFrontendDeps();
}
ensureHusky();
