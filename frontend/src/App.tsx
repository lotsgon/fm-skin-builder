import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { Folder, Play, Package, Bug, Loader2, Terminal, CheckCircle2, XCircle, StopCircle } from 'lucide-react';

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

type LogLevel = 'info' | 'error' | 'warning';

type LogEntry = {
  message: string;
  level: LogLevel;
  timestamp: string;
};

type BuildProgress = {
  current: number;
  total: number;
  status: string;
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
  const [logs, setLogs] = useState<LogEntry[]>([
    { message: 'Ready to build', level: 'info', timestamp: new Date().toLocaleTimeString() }
  ]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentTask, setCurrentTask] = useState<string | null>(null);
  const [buildProgress, setBuildProgress] = useState<BuildProgress | null>(null);
  const [lastBuildSuccess, setLastBuildSuccess] = useState<boolean | null>(null);
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

  // Set up event listeners for real-time build feedback
  useEffect(() => {
    let unlistenLog: (() => void) | null = null;
    let unlistenProgress: (() => void) | null = null;
    let unlistenComplete: (() => void) | null = null;
    let unlistenTaskStarted: (() => void) | null = null;

    const setupListeners = async () => {
      // Listen for task started event
      unlistenTaskStarted = await listen<{ message: string }>(
        'task_started',
        (event) => {
          const timestamp = new Date().toLocaleTimeString();
          setLogs((prev) => [
            ...prev,
            {
              message: event.payload.message,
              level: 'info',
              timestamp,
            },
          ]);
        }
      );

      // Listen for log events
      unlistenLog = await listen<{ message: string; level: string }>(
        'build_log',
        (event) => {
          const timestamp = new Date().toLocaleTimeString();
          setLogs((prev) => [
            ...prev,
            {
              message: event.payload.message,
              level: event.payload.level as LogLevel,
              timestamp,
            },
          ]);
        }
      );

      // Listen for progress events
      unlistenProgress = await listen<{ current: number; total: number; status: string }>(
        'build_progress',
        (event) => {
          setBuildProgress({
            current: event.payload.current,
            total: event.payload.total,
            status: event.payload.status,
          });
        }
      );

      // Listen for completion events
      unlistenComplete = await listen<{ success: boolean; exit_code: number; message: string }>(
        'build_complete',
        (event) => {
          setIsRunning(false);
          setCurrentTask(null);
          setLastBuildSuccess(event.payload.success);
          setBuildProgress(null);

          const timestamp = new Date().toLocaleTimeString();
          setLogs((prev) => [
            ...prev,
            {
              message: event.payload.message,
              level: event.payload.success ? 'info' : 'error',
              timestamp,
            },
          ]);
        }
      );
    };

    setupListeners();

    // Cleanup listeners on unmount
    return () => {
      if (unlistenLog) unlistenLog();
      if (unlistenProgress) unlistenProgress();
      if (unlistenComplete) unlistenComplete();
      if (unlistenTaskStarted) unlistenTaskStarted();
    };
  }, []);

  const markRuntimeReady = useCallback(() => {
    setRuntimeState('ready');
  }, []);

  const appendLog = useCallback((message: string, level: LogLevel = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { message, level, timestamp }]);
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
        appendLog(`Folder picker failed: ${String(error)}`, 'error');
        setActiveTab('logs');
      }
    },
    [appendLog, bundlesPath, markRuntimeReady, skinPath]
  );

  const runTask = useCallback(
    async (mode: TaskMode) => {
      const config = buildConfig(mode);
      if (!config.skinPath) {
        appendLog('ERROR: Skin folder is required.', 'error');
        setActiveTab('logs');
        return;
      }

      setIsRunning(true);
      setLastBuildSuccess(null);
      setBuildProgress(null);
      setCurrentTask(mode === 'preview' ? 'Previewing Build' : 'Building Bundles');
      setActiveTab('logs');

      appendLog(`Starting ${mode === 'preview' ? 'preview' : 'build'} for: ${config.skinPath}`);
      appendLog(`Mode: ${config.dryRun ? 'dry run' : 'write mode'}`);
      if (config.debugExport) {
        appendLog('Debug mode: enabled');
      }

      try {
        // The command will now stream logs in real-time via events
        const response = await invoke<CommandResult>('run_python_task', {
          config
        });
        markRuntimeReady();

        // Note: Most logs are already displayed via events, but we handle
        // any remaining output here for backward compatibility
        if (response.stdout.trim().length) {
          const lines = response.stdout.trim().split('\n');
          // Filter out lines we've already shown via events
          const newLines = lines.filter(line => {
            // Simple dedup: if the last 10 logs contain this line, skip it
            const recent = logs.slice(-10).map(l => l.message);
            return !recent.includes(line);
          });
          newLines.forEach((line) => appendLog(line));
        }
      } catch (error) {
        appendLog(`✗ Command failed: ${String(error)}`, 'error');
        setIsRunning(false);
        setCurrentTask(null);
        setLastBuildSuccess(false);
      }
    },
    [appendLog, buildConfig, markRuntimeReady, logs]
  );

  const clearLogs = useCallback(() => {
    setLogs([{ message: 'Ready to build', level: 'info', timestamp: new Date().toLocaleTimeString() }]);
    setLastBuildSuccess(null);
    setBuildProgress(null);
  }, []);

  const stopTask = useCallback(async () => {
    try {
      const result = await invoke<string>('stop_python_task');
      appendLog(`Task cancelled: ${result}`, 'warning');
      setIsRunning(false);
      setCurrentTask(null);
      setBuildProgress(null);
      setLastBuildSuccess(false);
    } catch (error) {
      appendLog(`Failed to stop task: ${String(error)}`, 'error');
    }
  }, [appendLog]);

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

  const progressPercentage = useMemo(() => {
    if (!buildProgress || buildProgress.total === 0) return 0;
    return Math.round((buildProgress.current / buildProgress.total) * 100);
  }, [buildProgress]);

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

            {/* Last Build Status */}
            {lastBuildSuccess !== null && (
              <Card className={lastBuildSuccess ? 'border-green-500/50 bg-green-500/5' : 'border-red-500/50 bg-red-500/5'}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    {lastBuildSuccess ? (
                      <>
                        <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
                        <div>
                          <p className="font-semibold text-green-600 dark:text-green-400">Build Successful</p>
                          <p className="text-sm text-muted-foreground">Your skin has been built successfully</p>
                        </div>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
                        <div>
                          <p className="font-semibold text-red-600 dark:text-red-400">Build Failed</p>
                          <p className="text-sm text-muted-foreground">Check the logs for error details</p>
                        </div>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="logs" className="space-y-4">
            {/* Progress Card */}
            {isRunning && (
              <Card className="border-primary/50 bg-primary/5">
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{currentTask}</span>
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={stopTask}
                          className="gap-1.5"
                        >
                          <StopCircle className="h-3.5 w-3.5" />
                          Stop
                        </Button>
                      </div>
                    </div>

                    {buildProgress && buildProgress.total > 0 ? (
                      <>
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>
                              Bundle {buildProgress.current} of {buildProgress.total}
                            </span>
                            <span>{progressPercentage}%</span>
                          </div>
                          <Progress value={progressPercentage} className="h-2" />
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {buildProgress.status}
                        </p>
                      </>
                    ) : (
                      <>
                        <Progress value={undefined} className="h-2" />
                        <p className="text-xs text-muted-foreground">
                          Processing... Check logs below for details
                        </p>
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Logs Card */}
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
                          log.level === 'error'
                            ? 'text-destructive'
                            : log.level === 'warning'
                              ? 'text-yellow-600 dark:text-yellow-400'
                              : log.message.includes('✓') || log.message.includes('✅')
                                ? 'text-green-600 dark:text-green-400'
                                : 'text-foreground'
                        }
                      >
                        <span className="text-muted-foreground">[{log.timestamp}]</span> {log.message}
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
