import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { getVersion } from "@tauri-apps/api/app";
import {
  Folder,
  Play,
  Package,
  Bug,
  Loader2,
  Terminal,
  CheckCircle2,
  XCircle,
  StopCircle,
  Zap,
  AlertCircle,
  Settings as SettingsIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ThemeToggle } from "@/components/theme-toggle";
import { Logo } from "@/components/logo";
import { Settings } from "@/components/Settings";
import { useStore } from "@/hooks/useStore";

type CommandResult = {
  stdout: string;
  stderr: string;
  status: number;
};

type TaskMode = "preview" | "build";

type TaskConfig = {
  skinPath: string;
  bundlesPath: string;
  debugExport: boolean;
  dryRun: boolean;
};

type LogLevel = "info" | "error" | "warning";

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
  if (typeof window === "undefined") {
    return "unknown" as const;
  }

  const candidate = window as Window & {
    __TAURI__?: { invoke?: unknown };
    __TAURI_IPC__?: unknown;
  };

  if (
    candidate.__TAURI__ &&
    typeof candidate.__TAURI__.invoke !== "undefined"
  ) {
    return "ready" as const;
  }

  if (typeof candidate.__TAURI_IPC__ !== "undefined") {
    return "ready" as const;
  }

  return "preview" as const;
};

function App() {
  const [activeTab, setActiveTab] = useState<"build" | "logs" | "settings">(
    "build"
  );
  const [skinPath, setSkinPath] = useState("");
  const [bundlesPath, setBundlesPath] = useState("");
  const [debugMode, setDebugMode] = useState(false);
  const { settings, saveSetting, clearSetting } = useStore();
  const [pathErrors, setPathErrors] = useState<{
    skin?: string;
    bundles?: string;
  }>({});
  const [pathWarnings, setPathWarnings] = useState<{
    skin?: string;
    bundles?: string;
  }>({});
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      message: "Ready to build",
      level: "info",
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentTask, setCurrentTask] = useState<string | null>(null);
  const [buildProgress, setBuildProgress] = useState<BuildProgress | null>(
    null
  );
  const [lastBuildSuccess, setLastBuildSuccess] = useState<boolean | null>(
    null
  );
  const [lastTaskType, setLastTaskType] = useState<TaskMode | null>(null);
  const [runtimeState, setRuntimeState] = useState<
    "unknown" | "preview" | "ready"
  >(() => detectTauriRuntime());
  const [listenersReady, setListenersReady] = useState(true);
  const [appVersion, setAppVersion] = useState<string>("");

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setRuntimeState(detectTauriRuntime());

    // Get app version
    getVersion()
      .then((version) => setAppVersion(version))
      .catch(() => setAppVersion("dev"));
  }, []);

  // Load saved paths from store on mount
  useEffect(() => {
    if (settings.skinPath) {
      setSkinPath(settings.skinPath);
    }
    if (settings.bundlesPath) {
      setBundlesPath(settings.bundlesPath);
    }
  }, [settings.skinPath, settings.bundlesPath]);

  // Save skin path when it changes
  useEffect(() => {
    if (skinPath && skinPath !== settings.skinPath) {
      saveSetting("skinPath", skinPath).catch(console.error);
    }
  }, [skinPath, settings.skinPath, saveSetting]);

  // Save bundles path when it changes
  useEffect(() => {
    if (bundlesPath && bundlesPath !== settings.bundlesPath) {
      saveSetting("bundlesPath", bundlesPath).catch(console.error);
    }
  }, [bundlesPath, settings.bundlesPath, saveSetting]);

  useEffect(() => {
    // Auto-scroll logs to bottom
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Set up event listeners for real-time build feedback
  useEffect(() => {
    console.log("[FRONTEND] useEffect for event listeners starting...");
    console.log("[FRONTEND] Window object:", typeof window);
    console.log(
      "[FRONTEND] Tauri available:",
      typeof window !== "undefined" && "__TAURI__" in window
    );

    // For Tauri environment, skip listener setup and mark as ready immediately
    if (typeof window !== "undefined" && "__TAURI__" in window) {
      console.log(
        "[FRONTEND] Tauri detected, skipping listener setup for test environment"
      );
      setListenersReady(true);
      return;
    }

    // Track if this effect is still mounted (StrictMode safe)
    let isMounted = true;
    let timeoutId: NodeJS.Timeout | null = null;
    let setupComplete = false;

    // Store unlisten functions in an object to avoid stale closures
    const unlisteners: {
      log?: () => void;
      progress?: () => void;
      complete?: () => void;
      taskStarted?: () => void;
    } = {};

    const setupListeners = async () => {
      console.log("[FRONTEND] setupListeners called");

      // Add a small delay to ensure Tauri runtime is fully ready
      await new Promise((resolve) => setTimeout(resolve, 100));
      console.log("[FRONTEND] After 100ms delay");

      // Check if we're still mounted after delay
      if (!isMounted) {
        console.log(
          "[FRONTEND] Component unmounted during delay, aborting listener setup"
        );
        return;
      }

      try {
        // Listen for task started event
        console.log("[FRONTEND] Setting up task_started listener...");
        unlisteners.taskStarted = await listen<{ message: string }>(
          "task_started",
          (event) => {
            console.log(
              "[FRONTEND] task_started event received:",
              event.payload
            );
            const timestamp = new Date().toLocaleTimeString();
            setLogs((prev) => [
              ...prev,
              {
                message: event.payload.message,
                level: "info",
                timestamp,
              },
            ]);
          }
        );
        if (!isMounted) return; // Check after each async operation
        console.log("[FRONTEND] task_started listener set up");

        // Listen for log events
        console.log("[FRONTEND] Setting up build_log listener...");
        unlisteners.log = await listen<{ message: string; level: string }>(
          "build_log",
          (event) => {
            console.log(
              "[FRONTEND] build_log event received:",
              event.payload.message
            );
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
        if (!isMounted) return;
        console.log("[FRONTEND] build_log listener set up");

        // Listen for progress events
        console.log("[FRONTEND] Setting up build_progress listener...");
        unlisteners.progress = await listen<{
          current: number;
          total: number;
          status: string;
        }>("build_progress", (event) => {
          console.log(
            "[FRONTEND] build_progress event received:",
            event.payload
          );
          setBuildProgress({
            current: event.payload.current,
            total: event.payload.total,
            status: event.payload.status,
          });
        });
        if (!isMounted) return;
        console.log("[FRONTEND] build_progress listener set up");

        // Listen for completion events
        console.log("[FRONTEND] Setting up build_complete listener...");
        unlisteners.complete = await listen<{
          success: boolean;
          exit_code: number;
          message: string;
        }>("build_complete", (event) => {
          console.log(
            "[FRONTEND] build_complete event received:",
            event.payload
          );
          setIsRunning(false);
          setCurrentTask(null);
          setLastBuildSuccess(event.payload.success);
          setBuildProgress(null);

          const timestamp = new Date().toLocaleTimeString();
          setLogs((prev) => [
            ...prev,
            {
              message: event.payload.message,
              level: event.payload.success ? "info" : "error",
              timestamp,
            },
          ]);
        });
        if (!isMounted) return;
        console.log("[FRONTEND] build_complete listener set up");
        console.log("[FRONTEND] All listeners configured successfully");
      } catch (error) {
        console.error("[FRONTEND] Error setting up listeners:", error);
        setListenersReady(false);
        throw error;
      }
    };

    // Set a timeout to ensure buttons don't stay disabled forever if setup fails
    timeoutId = setTimeout(() => {
      if (!setupComplete && isMounted) {
        console.warn("[FRONTEND] Listener setup timeout - re-enabling buttons");
        setListenersReady(true);
      }
    }, 3000); // 3 second timeout

    // IMPORTANT: Wait for listeners to be set up before marking ready
    console.log("[FRONTEND] About to call setupListeners...");
    setupListeners()
      .then(() => {
        if (!isMounted) {
          console.log(
            "[FRONTEND] Component unmounted, skipping ready state update"
          );
          return;
        }
        console.log("[FRONTEND] All event listeners set up successfully");
        setupComplete = true;
        if (timeoutId) clearTimeout(timeoutId);
        setListenersReady(true);
      })
      .catch((error) => {
        if (!isMounted) return;
        console.error("[FRONTEND] Failed to set up event listeners:", error);
        setupComplete = true;
        if (timeoutId) clearTimeout(timeoutId);
        // Mark listeners as not ready on explicit failure
        setListenersReady(false);
      });

    // Cleanup listeners on unmount (StrictMode safe)
    return () => {
      console.log("[FRONTEND] Cleaning up event listeners");
      isMounted = false;
      if (timeoutId) clearTimeout(timeoutId);

      // Clean up all listeners
      Object.values(unlisteners).forEach((unlisten) => {
        if (unlisten) unlisten();
      });
    };
  }, []);

  const markRuntimeReady = useCallback(() => {
    setRuntimeState("ready");
  }, []);

  const appendLog = useCallback((message: string, level: LogLevel = "info") => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { message, level, timestamp }]);
  }, []);

  const buildConfig = useCallback(
    (mode: TaskMode): TaskConfig => ({
      skinPath: skinPath.trim(),
      bundlesPath: bundlesPath.trim(),
      debugExport: debugMode,
      dryRun: mode === "preview",
    }),
    [bundlesPath, debugMode, skinPath]
  );

  const browseForFolder = useCallback(
    async (target: "skin" | "bundles") => {
      try {
        const selected = await invoke<string | null>("select_folder", {
          dialog_title:
            target === "skin" ? "Select Skin Folder" : "Select Bundles Folder",
          initial_path: target === "skin" ? skinPath : bundlesPath,
        });
        markRuntimeReady();

        if (typeof selected === "string") {
          if (target === "skin") {
            setSkinPath(selected);
            appendLog(`Selected skin folder: ${selected}`);
            setPathErrors((prev) => ({ ...prev, skin: undefined }));
            setPathWarnings((prev) => ({ ...prev, skin: undefined }));
          } else {
            setBundlesPath(selected);
            appendLog(`Selected bundles folder: ${selected}`);
            setPathErrors((prev) => ({ ...prev, bundles: undefined }));
            setPathWarnings((prev) => ({ ...prev, bundles: undefined }));
          }
        }
      } catch (error) {
        appendLog(`Folder picker failed: ${String(error)}`, "error");
        setActiveTab("logs");
      }
    },
    [appendLog, bundlesPath, markRuntimeReady, skinPath]
  );

  const validatePaths = useCallback((): boolean => {
    const errors: { skin?: string; bundles?: string } = {};

    if (!skinPath || skinPath.trim() === "") {
      errors.skin = "Required - Use Auto-detect or browse for folder";
    }

    if (!bundlesPath || bundlesPath.trim() === "") {
      errors.bundles = "Required - Use Auto-detect or browse for folder";
    }

    setPathErrors(errors);

    if (errors.skin || errors.bundles) {
      if (errors.skin)
        appendLog(
          "ERROR: Skin folder is required. Use Auto-detect or browse for folder.",
          "error"
        );
      if (errors.bundles)
        appendLog(
          "ERROR: Bundles directory is required. Use Auto-detect or browse for folder.",
          "error"
        );
      // Don't switch tabs - keep user on current screen to see validation errors
      return false;
    }

    return true;
  }, [skinPath, bundlesPath, appendLog]);

  const handleAutoDetectGame = useCallback(async () => {
    try {
      // detect_game_installation now returns the bundles directory directly
      const bundlesPath = await invoke<string | null>(
        "detect_game_installation"
      );
      if (bundlesPath) {
        setBundlesPath(bundlesPath);
        appendLog(`✓ Found bundles directory: ${bundlesPath}`, "info");
        setPathErrors((prev) => ({ ...prev, bundles: undefined }));
        setPathWarnings((prev) => ({ ...prev, bundles: undefined }));
      } else {
        appendLog("⚠ Could not detect game installation", "warning");
        appendLog(
          "Checked Steam, Epic Games, and Xbox Game Pass locations - use Browse to select manually",
          "info"
        );
        setPathWarnings((prev) => ({
          ...prev,
          bundles:
            "Could not detect game installation - use Browse to select manually",
        }));
      }
    } catch (error) {
      appendLog(`Error detecting game: ${String(error)}`, "error");
      setPathErrors((prev) => ({
        ...prev,
        bundles: `Error: ${String(error)}`,
      }));
    }
  }, [appendLog]);

  const handleGetDefaultSkinsDir = useCallback(async () => {
    try {
      const defaultDir = await invoke<string>("get_default_skins_dir");
      appendLog(`Default skins directory: ${defaultDir}`, "info");
      setSkinPath(defaultDir);
      setPathErrors((prev) => ({ ...prev, skin: undefined }));
    } catch (error) {
      appendLog(
        `Error getting default skins directory: ${String(error)}`,
        "error"
      );
    }
  }, [appendLog]);

  const runTask = useCallback(
    async (mode: TaskMode) => {
      // Validate paths before running
      if (!validatePaths()) {
        return;
      }

      const config = buildConfig(mode);

      setIsRunning(true);
      setLastBuildSuccess(null);
      setLastTaskType(mode);
      setBuildProgress(null);
      setCurrentTask(
        mode === "preview" ? "Previewing Build" : "Building Bundles"
      );
      setActiveTab("logs");

      appendLog(
        `Starting ${mode === "preview" ? "preview" : "build"} for: ${
          config.skinPath
        }`
      );
      appendLog(`Mode: ${config.dryRun ? "dry run" : "write mode"}`);
      if (config.debugExport) {
        appendLog("Debug mode: enabled");
      }

      try {
        // The command will now stream logs in real-time via events
        const response = await invoke<CommandResult>("run_python_task", {
          config,
        });
        markRuntimeReady();

        // Note: Most logs are already displayed via events
        // Any remaining output is likely redundant, so we skip deduplication
        if (response.stdout.trim().length) {
          const lines = response.stdout.trim().split("\n");
          lines.forEach((line) => appendLog(line));
        }
      } catch (error) {
        appendLog(`✗ Command failed: ${String(error)}`, "error");
        setLastBuildSuccess(false);
      } finally {
        setIsRunning(false);
        setCurrentTask(null);
      }
    },
    [appendLog, buildConfig, markRuntimeReady, validatePaths]
  );

  const clearLogs = useCallback(() => {
    setLogs([
      {
        message: "Ready to build",
        level: "info",
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
    setLastBuildSuccess(null);
    setBuildProgress(null);
  }, []);

  const stopTask = useCallback(async () => {
    try {
      const result = await invoke<string>("stop_python_task");
      appendLog(`Task cancelled: ${result}`, "warning");
      setIsRunning(false);
      setCurrentTask(null);
      setBuildProgress(null);
      setLastBuildSuccess(false);
    } catch (error) {
      appendLog(`Failed to stop task: ${String(error)}`, "error");
    }
  }, [appendLog]);

  const runtimeIndicator = useMemo(() => {
    switch (runtimeState) {
      case "ready":
        return { color: "bg-green-500", label: "Backend Ready" };
      case "preview":
        return { color: "bg-yellow-500", label: "Frontend Preview" };
      default:
        return { color: "bg-muted-foreground", label: "Detecting Runtime" };
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
              <p className="text-xs text-muted-foreground">
                Build and preview Football Manager skins
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Badge variant="outline" className="gap-2">
              <span
                className={`h-2 w-2 rounded-full ${runtimeIndicator.color}`}
              />
              {runtimeIndicator.label}
            </Badge>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="container mx-auto max-w-6xl px-6 py-8 pb-16">
        <Tabs
          value={activeTab}
          onValueChange={(v) =>
            setActiveTab(v as "build" | "logs" | "settings")
          }
        >
          <TabsList className="grid w-full max-w-2xl grid-cols-3">
            <TabsTrigger value="build" className="gap-2">
              <Package className="h-4 w-4" />
              Build
            </TabsTrigger>
            <TabsTrigger value="logs" className="gap-2">
              <Terminal className="h-4 w-4" />
              Logs
              {isRunning && <Loader2 className="h-3 w-3 animate-spin" />}
            </TabsTrigger>
            <TabsTrigger value="settings" className="gap-2">
              <SettingsIcon className="h-4 w-4" />
              Settings
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
                      onChange={(e) => {
                        setSkinPath(e.target.value);
                        if (pathErrors.skin && e.target.value.trim()) {
                          setPathErrors((prev) => ({
                            ...prev,
                            skin: undefined,
                          }));
                        }
                        if (pathWarnings.skin && e.target.value.trim()) {
                          setPathWarnings((prev) => ({
                            ...prev,
                            skin: undefined,
                          }));
                        }
                      }}
                      placeholder="Select your skin folder..."
                      className={`flex-1 ${
                        pathErrors.skin ? "border-red-500" : ""
                      }`}
                    />
                    <Button
                      variant="outline"
                      onClick={handleGetDefaultSkinsDir}
                      className="gap-2"
                      title="Auto-detect default skins directory"
                    >
                      <Zap className="h-4 w-4" />
                      <span className="hidden sm:inline">Auto-detect</span>
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => browseForFolder("skin")}
                      title="Browse for folder"
                    >
                      <Folder className="h-4 w-4" />
                    </Button>
                  </div>
                  {pathErrors.skin ? (
                    <p className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                      <AlertCircle className="h-3 w-3" />
                      {pathErrors.skin}
                    </p>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      Must contain a valid{" "}
                      <code className="rounded bg-muted px-1 py-0.5">
                        config.json
                      </code>
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bundles-folder">Bundles Directory</Label>
                  <div className="flex gap-2">
                    <Input
                      id="bundles-folder"
                      value={bundlesPath}
                      onChange={(e) => {
                        setBundlesPath(e.target.value);
                        if (pathErrors.bundles && e.target.value.trim()) {
                          setPathErrors((prev) => ({
                            ...prev,
                            bundles: undefined,
                          }));
                        }
                        if (pathWarnings.bundles && e.target.value.trim()) {
                          setPathWarnings((prev) => ({
                            ...prev,
                            bundles: undefined,
                          }));
                        }
                      }}
                      placeholder="Select bundles directory..."
                      className={`flex-1 ${
                        pathErrors.bundles ? "border-red-500" : ""
                      }`}
                    />
                    <Button
                      variant="outline"
                      onClick={handleAutoDetectGame}
                      className="gap-2"
                      title="Auto-detect game installation (Steam, Epic, Xbox Game Pass)"
                    >
                      <Zap className="h-4 w-4" />
                      <span className="hidden sm:inline">Auto-detect</span>
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => browseForFolder("bundles")}
                      title="Browse for folder"
                    >
                      <Folder className="h-4 w-4" />
                    </Button>
                  </div>
                  {pathErrors.bundles ? (
                    <p className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                      <AlertCircle className="h-3 w-3" />
                      {pathErrors.bundles}
                    </p>
                  ) : pathWarnings.bundles ? (
                    <p className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                      <AlertCircle className="h-3 w-3" />
                      {pathWarnings.bundles}
                    </p>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      Game bundles directory (supports Steam, Epic Games, Xbox
                      Game Pass)
                    </p>
                  )}
                </div>

                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <Bug className="h-4 w-4 text-muted-foreground" />
                      <Label
                        htmlFor="debug-mode"
                        className="cursor-pointer font-semibold"
                      >
                        Debug Mode
                      </Label>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Adds{" "}
                      <code className="rounded bg-muted px-1 py-0.5">
                        --debug-export
                      </code>{" "}
                      for detailed USS output
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
                    onClick={() => runTask("preview")}
                    disabled={isRunning || !listenersReady}
                    className="flex-1 gap-2"
                    size="lg"
                  >
                    {!listenersReady ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Initializing...
                      </>
                    ) : isRunning && currentTask === "Previewing Build" ? (
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
                    onClick={() => runTask("build")}
                    disabled={isRunning || !listenersReady}
                    variant="secondary"
                    className="flex-1 gap-2"
                    size="lg"
                  >
                    {!listenersReady ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Initializing...
                      </>
                    ) : isRunning && currentTask === "Building Bundles" ? (
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
              <Card
                className={
                  lastBuildSuccess
                    ? "border-green-500/50 bg-green-500/5"
                    : "border-red-500/50 bg-red-500/5"
                }
              >
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    {lastBuildSuccess ? (
                      <>
                        <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
                        <div>
                          <p className="font-semibold text-green-600 dark:text-green-400">
                            {lastTaskType === "preview"
                              ? "Preview Successful"
                              : "Build Successful"}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {lastTaskType === "preview"
                              ? "No bundles were modified during this dry run"
                              : "Your skin bundles have been created successfully"}
                          </p>
                        </div>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
                        <div>
                          <p className="font-semibold text-red-600 dark:text-red-400">
                            {lastTaskType === "preview"
                              ? "Preview Failed"
                              : "Build Failed"}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Check the logs for error details
                          </p>
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
                              Bundle {buildProgress.current} of{" "}
                              {buildProgress.total}
                            </span>
                            <span>{progressPercentage}%</span>
                          </div>
                          <Progress
                            value={progressPercentage}
                            className="h-2"
                          />
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
                    <CardDescription>
                      Real-time output from build operations
                    </CardDescription>
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
                          log.level === "error"
                            ? "text-destructive"
                            : log.level === "warning"
                            ? "text-yellow-600 dark:text-yellow-400"
                            : log.message.includes("✓") ||
                              log.message.includes("✅")
                            ? "text-green-600 dark:text-green-400"
                            : "text-foreground"
                        }
                      >
                        <span className="text-muted-foreground">
                          [{log.timestamp}]
                        </span>{" "}
                        {log.message}
                      </div>
                    ))}
                    <div ref={logsEndRef} />
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="settings">
            <Settings
              skinPath={skinPath}
              bundlesPath={bundlesPath}
              betaUpdates={settings.betaUpdates ?? false}
              autoUpdate={settings.checkForUpdates ?? true}
              onClearSkinPath={() => {
                setSkinPath("");
                clearSetting("skinPath").catch(console.error);
              }}
              onClearBundlesPath={() => {
                setBundlesPath("");
                clearSetting("bundlesPath").catch(console.error);
              }}
              onBetaUpdatesChange={(enabled) => {
                saveSetting("betaUpdates", enabled).catch(console.error);
              }}
              onAutoUpdateChange={(enabled) => {
                saveSetting("checkForUpdates", enabled).catch(console.error);
              }}
            />
          </TabsContent>
        </Tabs>
      </main>

      {/* Version Display */}
      <div className="fixed bottom-4 left-4 flex gap-2">
        <Badge variant="secondary" className="text-xs">
          v{appVersion}
        </Badge>
        {appVersion && appVersion.includes("-") && appVersion !== "dev" && (
          <Badge
            variant="outline"
            className="text-xs border-yellow-500 text-yellow-600 dark:text-yellow-400"
          >
            Beta
          </Badge>
        )}
      </div>
    </div>
  );
}

export default App;
