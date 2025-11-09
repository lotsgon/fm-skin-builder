import { useCallback, useEffect, useMemo, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';

type CommandResult = {
  stdout: string;
  stderr: string;
  status: number;
};

const tabs = [
  { id: 'build', label: 'Build' },
  { id: 'logs', label: 'Logs' }
] as const;

type TabId = (typeof tabs)[number]['id'];
type TaskMode = 'preview' | 'build';

type TaskConfig = {
  skinPath: string;
  bundlesPath: string;
  debugExport: boolean;
  dryRun: boolean;
};

const detectTauriRuntime = () => {
  if (typeof window === 'undefined') {
    return 'unknown' as const;
  }

  const candidate = window as Window & {
    __TAURI__?: { invoke?: unknown };
    __TAURI_IPC__?: unknown;
  };

  if (candidate.__TAURI__ && typeof candidate.__TAURI__.invoke !== 'undefined') {
    return 'ready' as const;
  }

  if (typeof candidate.__TAURI_IPC__ !== 'undefined') {
    return 'ready' as const;
  }

  return 'preview' as const;
};

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('build');
  const [skinPath, setSkinPath] = useState('skins/test_skin');
  const [bundlesPath, setBundlesPath] = useState('bundles');
  const [debugMode, setDebugMode] = useState(false);
  const [logs, setLogs] = useState<string[]>(['Idle']);
  const [isRunning, setIsRunning] = useState(false);
  const [runtimeState, setRuntimeState] = useState<'unknown' | 'preview' | 'ready'>(
    () => detectTauriRuntime()
  );

  const taskCopy = useMemo(
    () => ({
      preview: 'Preview Build',
      build: 'Build Bundles'
    }),
    []
  );

  useEffect(() => {
    setRuntimeState(detectTauriRuntime());
  }, []);

  const markRuntimeReady = useCallback(() => {
    setRuntimeState('ready');
  }, []);

  const appendLog = useCallback((line: string) => {
    setLogs((prev) => [...prev.filter(Boolean), line]);
  }, []);

  const buildConfig = useCallback(
    (mode: TaskMode): TaskConfig => ({
      skinPath: skinPath.trim(),
      bundlesPath: bundlesPath.trim(),
      debugExport: debugMode,
      dryRun: mode === 'preview'
    }),
    [bundlesPath, debugMode, skinPath]
  );

  const browseForFolder = useCallback(
    async (target: 'skin' | 'bundles') => {
      try {
        const selected = await invoke<string | null>('select_folder', {
          dialog_title: target === 'skin' ? 'Select Skin Folder' : 'Select Bundles Folder',
          initial_path: target === 'skin' ? skinPath : bundlesPath
        });
        markRuntimeReady();

        if (typeof selected === 'string') {
          if (target === 'skin') {
            setSkinPath(selected);
          } else {
            setBundlesPath(selected);
          }
        }
      } catch (error) {
        appendLog(`Folder picker failed: ${String(error)}`);
        setActiveTab('logs');
      }
    },
    [appendLog, bundlesPath, markRuntimeReady, skinPath]
  );

  const runTask = useCallback(
    async (mode: TaskMode) => {
      const config = buildConfig(mode);
      if (!config.skinPath) {
        appendLog('Skin folder is required.');
        setActiveTab('logs');
        return;
      }

      setIsRunning(true);
      appendLog(
        `${taskCopy[mode]} for skin "${config.skinPath}" (${config.dryRun ? 'dry run' : 'write mode'})`
      );

      try {
        const response = await invoke<CommandResult>('run_python_task', {
          config
        });
        markRuntimeReady();

        if (response.stdout.trim().length) {
          appendLog(response.stdout.trim());
        }
        if (response.stderr.trim().length) {
          appendLog(`[stderr] ${response.stderr.trim()}`);
        }
        appendLog(`Process exited with status ${response.status}`);
        setActiveTab('logs');
      } catch (error) {
        appendLog(`Command failed: ${String(error)}`);
        setActiveTab('logs');
      } finally {
        setIsRunning(false);
      }
    },
    [appendLog, buildConfig, markRuntimeReady, taskCopy]
  );

  const runtimeIndicator = useMemo(() => {
    switch (runtimeState) {
      case 'ready':
        return { color: 'bg-green-400', label: 'Backend Ready' };
      case 'preview':
        return { color: 'bg-yellow-400', label: 'Frontend Preview' };
      default:
        return { color: 'bg-muted', label: 'Detecting Runtime' };
    }
  }, [runtimeState]);

  return (
    <div className="min-h-screen bg-surface text-foreground">
      <header className="bg-panel shadow-toolbar border-b border-border">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <div>
            <h1 className="text-lg font-semibold">FM Skin Builder</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className={`h-2 w-2 rounded-full ${runtimeIndicator.color}`} />
            <span className="text-sm text-muted">{runtimeIndicator.label}</span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-4 flex gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-accent text-black shadow-panel'
                  : 'bg-panel text-muted hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <section className="rounded-2xl bg-panel shadow-panel">
          {activeTab === 'build' ? (
            <div className="space-y-6 p-6">
              <div>
                <label className="text-sm font-semibold text-muted" htmlFor="skin-folder">
                  Skin Folder
                </label>
                <div className="mt-2 flex gap-3">
                  <input
                    id="skin-folder"
                    value={skinPath}
                    onChange={(event) => setSkinPath(event.target.value)}
                    className="w-full rounded-lg border border-border bg-surface px-4 py-3 text-sm focus:border-accent focus:outline-none"
                    placeholder="skins/test_skin"
                  />
                  <button
                    type="button"
                    onClick={() => browseForFolder('skin')}
                    className="rounded-lg border border-border px-4 text-sm font-medium text-muted hover:text-foreground"
                  >
                    Browse
                  </button>
                </div>
                <p className="mt-2 text-xs text-muted">
                  Must contain a valid <code>config.json</code>.
                </p>
              </div>

              <div>
                <label className="text-sm font-semibold text-muted" htmlFor="bundles-folder">
                  Bundles Directory
                </label>
                <div className="mt-2 flex gap-3">
                  <input
                    id="bundles-folder"
                    value={bundlesPath}
                    onChange={(event) => setBundlesPath(event.target.value)}
                    className="w-full rounded-lg border border-border bg-surface px-4 py-3 text-sm focus:border-accent focus:outline-none"
                    placeholder="bundles"
                  />
                  <button
                    type="button"
                    onClick={() => browseForFolder('bundles')}
                    className="rounded-lg border border-border px-4 text-sm font-medium text-muted hover:text-foreground"
                  >
                    Browse
                  </button>
                </div>
                <p className="mt-2 text-xs text-muted">Overrides `--bundle` when provided.</p>
              </div>

              <div className="flex items-center justify-between rounded-xl border border-border bg-surface px-4 py-3">
                <div>
                  <p className="text-sm font-semibold">Debug Mode</p>
                  <p className="text-xs text-muted">Adds `--debug-export` for detailed USS output.</p>
                </div>
                <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium">
                  <span className="text-muted">Off</span>
                  <input
                    type="checkbox"
                    className="sr-only"
                    aria-label="Enable debug mode"
                    checked={debugMode}
                    onChange={(event) => setDebugMode(event.target.checked)}
                  />
                  <div
                    className={`h-6 w-12 rounded-full transition-colors ${
                      debugMode ? 'bg-accent/80' : 'bg-border'
                    }`}
                  >
                    <div
                      className={`h-6 w-6 rounded-full bg-panel shadow-toolbar transition-transform ${
                        debugMode ? 'translate-x-6' : 'translate-x-0'
                      }`}
                    />
                  </div>
                  <span className="text-muted">On</span>
                </label>
              </div>

              <div className="flex flex-wrap gap-4">
                <button
                  type="button"
                  onClick={() => runTask('preview')}
                  disabled={isRunning}
                  className="flex-1 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isRunning ? 'Running…' : 'Preview Build'}
                </button>
                <button
                  type="button"
                  onClick={() => runTask('build')}
                  disabled={isRunning}
                  className="flex-1 rounded-full border border-border px-6 py-3 text-sm font-semibold text-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Build Bundles
                </button>
              </div>
            </div>
          ) : (
            <div className="p-6">
              <div className="text-sm text-muted">Live Output</div>
              <pre className="scrollbar mt-3 h-72 overflow-y-auto rounded-xl border border-border bg-black/50 p-4 text-xs leading-relaxed text-green-200">
                {logs.length ? logs.join('\n\n') : 'No logs yet. Trigger a run to inspect output.'}
              </pre>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
