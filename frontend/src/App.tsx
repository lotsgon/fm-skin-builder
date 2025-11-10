import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Folder, Play, Package, Bug, Loader2, Terminal } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ThemeToggle } from '@/components/theme-toggle';
import { Logo } from '@/components/logo';

type CommandResult = {
  stdout: string;
  stderr: string;
  status: number;
};

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
  const [activeTab, setActiveTab] = useState<'build' | 'logs'>('build');
  const [skinPath, setSkinPath] = useState('skins/test_skin');
  const [bundlesPath, setBundlesPath] = useState('bundles');
  const [debugMode, setDebugMode] = useState(false);
  const [logs, setLogs] = useState<string[]>(['Ready to build']);
  const [isRunning, setIsRunning] = useState(false);
  const [currentTask, setCurrentTask] = useState<string | null>(null);
  const [runtimeState, setRuntimeState] = useState<'unknown' | 'preview' | 'ready'>(
    () => detectTauriRuntime()
  );

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setRuntimeState(detectTauriRuntime());
  }, []);

  useEffect(() => {
    // Auto-scroll logs to bottom
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const markRuntimeReady = useCallback(() => {
    setRuntimeState('ready');
  }, []);

  const appendLog = useCallback((line: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, `[${timestamp}] ${line}`]);
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
            appendLog(`Selected skin folder: ${selected}`);
          } else {
            setBundlesPath(selected);
            appendLog(`Selected bundles folder: ${selected}`);
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
        appendLog('ERROR: Skin folder is required.');
        setActiveTab('logs');
        return;
      }

      setIsRunning(true);
      setCurrentTask(mode === 'preview' ? 'Previewing Build' : 'Building Bundles');
      setActiveTab('logs');

      appendLog(`Starting ${mode === 'preview' ? 'preview' : 'build'} for: ${config.skinPath}`);
      appendLog(`Mode: ${config.dryRun ? 'dry run' : 'write mode'}`);
      if (config.debugExport) {
        appendLog('Debug mode: enabled');
      }

      try {
        const response = await invoke<CommandResult>('run_python_task', {
          config
        });
        markRuntimeReady();

        if (response.stdout.trim().length) {
          const lines = response.stdout.trim().split('\n');
          lines.forEach((line) => appendLog(line));
        }
        if (response.stderr.trim().length) {
          const lines = response.stderr.trim().split('\n');
          lines.forEach((line) => appendLog(`[STDERR] ${line}`));
        }

        if (response.status === 0) {
          appendLog(`✓ Process completed successfully`);
        } else {
          appendLog(`✗ Process exited with status ${response.status}`);
        }
      } catch (error) {
        appendLog(`✗ Command failed: ${String(error)}`);
      } finally {
        setIsRunning(false);
        setCurrentTask(null);
      }
    },
    [appendLog, buildConfig, markRuntimeReady]
  );

  const clearLogs = useCallback(() => {
    setLogs(['Ready to build']);
  }, []);

  const runtimeIndicator = useMemo(() => {
    switch (runtimeState) {
      case 'ready':
        return { color: 'bg-green-500', label: 'Backend Ready' };
      case 'preview':
        return { color: 'bg-yellow-500', label: 'Frontend Preview' };
      default:
        return { color: 'bg-muted-foreground', label: 'Detecting Runtime' };
    }
  }, [runtimeState]);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Logo />
            <div>
              <h1 className="text-lg font-bold">FM Skin Builder</h1>
              <p className="text-xs text-muted-foreground">Build and preview Football Manager skins</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Badge variant="outline" className="gap-2">
              <span className={`h-2 w-2 rounded-full ${runtimeIndicator.color}`} />
              {runtimeIndicator.label}
            </Badge>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="container mx-auto max-w-6xl px-6 py-8">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'build' | 'logs')}>
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="build" className="gap-2">
              <Package className="h-4 w-4" />
              Build
            </TabsTrigger>
            <TabsTrigger value="logs" className="gap-2">
              <Terminal className="h-4 w-4" />
              Logs
              {isRunning && <Loader2 className="h-3 w-3 animate-spin" />}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="build" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Build Configuration</CardTitle>
                <CardDescription>
                  Configure your skin folder and output settings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="skin-folder">Skin Folder</Label>
                  <div className="flex gap-2">
                    <Input
                      id="skin-folder"
                      value={skinPath}
                      onChange={(e) => setSkinPath(e.target.value)}
                      placeholder="skins/test_skin"
                      className="flex-1"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => browseForFolder('skin')}
                      title="Browse for folder"
                    >
                      <Folder className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Must contain a valid <code className="rounded bg-muted px-1 py-0.5">config.json</code>
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bundles-folder">Bundles Directory</Label>
                  <div className="flex gap-2">
                    <Input
                      id="bundles-folder"
                      value={bundlesPath}
                      onChange={(e) => setBundlesPath(e.target.value)}
                      placeholder="bundles"
                      className="flex-1"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => browseForFolder('bundles')}
                      title="Browse for folder"
                    >
                      <Folder className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Output directory for generated bundles
                  </p>
                </div>

                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <Bug className="h-4 w-4 text-muted-foreground" />
                      <Label htmlFor="debug-mode" className="cursor-pointer font-semibold">
                        Debug Mode
                      </Label>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Adds <code className="rounded bg-muted px-1 py-0.5">--debug-export</code> for
                      detailed USS output
                    </p>
                  </div>
                  <Switch
                    id="debug-mode"
                    checked={debugMode}
                    onCheckedChange={setDebugMode}
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <Button
                    onClick={() => runTask('preview')}
                    disabled={isRunning}
                    className="flex-1 gap-2"
                    size="lg"
                  >
                    {isRunning && currentTask === 'Previewing Build' ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" />
                        Preview Build
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={() => runTask('build')}
                    disabled={isRunning}
                    variant="secondary"
                    className="flex-1 gap-2"
                    size="lg"
                  >
                    {isRunning && currentTask === 'Building Bundles' ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Package className="h-4 w-4" />
                        Build Bundles
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="logs" className="space-y-4">
            {isRunning && (
              <Card className="border-primary/50 bg-primary/5">
                <CardContent className="pt-6">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{currentTask}</span>
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    </div>
                    <Progress value={undefined} className="h-2" />
                    <p className="text-xs text-muted-foreground">
                      Processing... Check logs below for details
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Build Logs</CardTitle>
                    <CardDescription>Real-time output from build operations</CardDescription>
                  </div>
                  <Button variant="outline" size="sm" onClick={clearLogs}>
                    Clear
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px] w-full rounded-md border bg-muted/30 p-4">
                  <div className="space-y-1 font-mono text-xs">
                    {logs.map((log, index) => (
                      <div
                        key={index}
                        className={
                          log.includes('ERROR') || log.includes('✗')
                            ? 'text-destructive'
                            : log.includes('✓')
                              ? 'text-green-600 dark:text-green-400'
                              : log.includes('[STDERR]')
                                ? 'text-yellow-600 dark:text-yellow-400'
                                : 'text-foreground'
                        }
                      >
                        {log}
                      </div>
                    ))}
                    <div ref={logsEndRef} />
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

export default App;
