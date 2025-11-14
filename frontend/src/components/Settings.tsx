import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { ask, message } from "@tauri-apps/plugin-dialog";
import { Button } from "./ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Label } from "./ui/label";
import { Switch } from "./ui/switch";
import {
  Loader2,
  FolderOpen,
  Trash2,
  Info,
  Settings as SettingsIcon,
  Download,
  AlertCircle,
} from "lucide-react";
import { useUpdater } from "../hooks/useUpdater";

type SettingsProps = {
  skinPath: string;
  bundlesPath: string;
  betaUpdates: boolean;
  autoUpdate: boolean;
  onClearSkinPath: () => void;
  onClearBundlesPath: () => void;
  onBetaUpdatesChange: (enabled: boolean) => void; // eslint-disable-line no-unused-vars
  onAutoUpdateChange: (enabled: boolean) => void; // eslint-disable-line no-unused-vars
};

export function Settings({
  skinPath,
  bundlesPath,
  betaUpdates,
  autoUpdate,
  onClearSkinPath,
  onClearBundlesPath,
  onBetaUpdatesChange,
  onAutoUpdateChange,
}: SettingsProps) {
  const [cacheSize, setCacheSize] = useState<number | null>(null);
  const [cacheDir, setCacheDir] = useState<string>("");
  const [defaultSkinsDir, setDefaultSkinsDir] = useState<string>("");
  const [appVersion, setAppVersion] = useState<string>("");
  const [platformInfo, setPlatformInfo] = useState<{
    os: string;
    arch: string;
    family: string;
  } | null>(null);
  const [isLoadingCache, setIsLoadingCache] = useState(false);
  const [isClearingCache, setIsClearingCache] = useState(false);

  // Use the updater hook
  const {
    isChecking,
    updateAvailable,
    latestVersion,
    currentVersion,
    releaseNotes,
    checkForUpdates,
  } = useUpdater({ autoUpdate, betaUpdates });

  // Load cache size and paths on mount
  useEffect(() => {
    async function loadInfo() {
      try {
        const [size, cache, skins, version, platform] = await Promise.all([
          invoke<number>("get_cache_size"),
          invoke<string>("get_cache_dir"),
          invoke<string>("get_default_skins_dir"),
          invoke<string>("get_app_version"),
          invoke<{ os: string; arch: string; family: string }>(
            "get_platform_info"
          ),
        ]);

        setCacheSize(size);
        setCacheDir(cache);
        setDefaultSkinsDir(skins);
        setAppVersion(version);
        setPlatformInfo(platform);
      } catch (error) {
        console.error("Failed to load settings info:", error);
      }
    }

    loadInfo();
  }, []);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const handleRefreshCacheSize = useCallback(async () => {
    setIsLoadingCache(true);
    try {
      const size = await invoke<number>("get_cache_size");
      setCacheSize(size);
    } catch (error) {
      console.error("Failed to refresh cache size:", error);
    } finally {
      setIsLoadingCache(false);
    }
  }, []);

  const handleClearCache = useCallback(async () => {
    console.log("[FRONTEND DEBUG] handleClearCache called!");
    console.log("[FRONTEND DEBUG] isClearingCache:", isClearingCache);
    console.log("[FRONTEND DEBUG] cacheSize:", cacheSize);

    const confirmed = await ask(
      "Are you sure you want to clear the cache? This will delete all cached skin configurations.",
      {
        title: "Clear Cache",
        kind: "warning",
      }
    );

    if (!confirmed) {
      console.log("[FRONTEND DEBUG] User cancelled confirmation");
      return;
    }

    console.log("[FRONTEND DEBUG] User confirmed, clearing cache...");
    setIsClearingCache(true);
    try {
      const backendMessage = await invoke<string>("clear_cache");
      console.log("[FRONTEND DEBUG] Backend response:", backendMessage);

      // Show success message using Tauri dialog
      await message(backendMessage, {
        title: "Success",
        kind: "info",
      });

      // Refresh cache size after clearing
      await handleRefreshCacheSize();
    } catch (error) {
      console.error("[FRONTEND DEBUG] Error clearing cache:", error);

      // Show error message using Tauri dialog
      await message(`Failed to clear cache: ${String(error)}`, {
        title: "Error",
        kind: "error",
      });
    } finally {
      setIsClearingCache(false);
    }
  }, [handleRefreshCacheSize, isClearingCache, cacheSize]);

  const handleOpenCacheDir = useCallback(async () => {
    try {
      await invoke("open_cache_dir");
    } catch (error) {
      alert(`Failed to open cache directory: ${String(error)}`);
    }
  }, []);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <SettingsIcon className="h-6 w-6" />
          Settings
        </h2>
        <p className="text-muted-foreground">
          Manage your application preferences and view system information
        </p>
      </div>

      {/* Paths Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderOpen className="h-5 w-5" />
            Paths
          </CardTitle>
          <CardDescription>Manage your saved folder locations</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Skin Folder</Label>
            <div className="flex gap-2 items-center">
              <div className="flex-1 text-sm text-muted-foreground truncate bg-muted px-3 py-2 rounded-md">
                {skinPath || "Not set"}
              </div>
              {skinPath && (
                <Button variant="outline" size="sm" onClick={onClearSkinPath}>
                  Clear
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label>Bundles Directory</Label>
            <div className="flex gap-2 items-center">
              <div className="flex-1 text-sm text-muted-foreground truncate bg-muted px-3 py-2 rounded-md">
                {bundlesPath || "Not set"}
              </div>
              {bundlesPath && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onClearBundlesPath}
                >
                  Clear
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label>Default Skins Directory</Label>
            <div className="flex gap-2 items-center">
              <div className="flex-1 text-sm text-muted-foreground truncate bg-muted px-3 py-2 rounded-md">
                {defaultSkinsDir}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Cache Directory</Label>
            <div className="flex gap-2 items-center">
              <div className="flex-1 text-sm text-muted-foreground truncate bg-muted px-3 py-2 rounded-md">
                {cacheDir}
              </div>
              <Button variant="outline" size="sm" onClick={handleOpenCacheDir}>
                Open
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Cache Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trash2 className="h-5 w-5" />
            Cache
          </CardTitle>
          <CardDescription>Manage cached skin configurations</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>Cache Size</Label>
              <p className="text-2xl font-bold">
                {cacheSize !== null ? formatBytes(cacheSize) : "..."}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshCacheSize}
              disabled={isLoadingCache}
            >
              {isLoadingCache ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Calculating...
                </>
              ) : (
                "Refresh"
              )}
            </Button>
          </div>

          <div className="pt-2">
            <Button
              variant="destructive"
              onClick={() => {
                console.log("[FRONTEND DEBUG] Clear Cache button clicked!");
                handleClearCache();
              }}
              disabled={isClearingCache}
            >
              {isClearingCache ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Clearing...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Clear Cache
                </>
              )}
            </Button>
            <p className="text-xs text-muted-foreground mt-2">
              Clearing the cache will delete all processed skin configurations.
              They will be regenerated on next build.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Updates Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Updates
          </CardTitle>
          <CardDescription>
            Configure automatic update preferences and check for new versions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Automatic Updates</Label>
              <p className="text-sm text-muted-foreground">
                Automatically check for and install updates on startup
              </p>
            </div>
            <Switch checked={autoUpdate} onCheckedChange={onAutoUpdateChange} />
          </div>

          <div className="flex items-center justify-between border-t pt-4">
            <div className="space-y-0.5">
              <Label>Enable Beta Updates</Label>
              <p className="text-sm text-muted-foreground">
                Receive early access to new features (may be unstable)
              </p>
            </div>
            <Switch
              checked={betaUpdates}
              onCheckedChange={onBetaUpdatesChange}
              disabled={!autoUpdate}
            />
          </div>

          <div className="pt-2 border-t">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label>Current Version</Label>
                  {updateAvailable && (
                    <AlertCircle className="h-4 w-4 text-orange-500" />
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <p className="text-lg font-semibold">
                    {currentVersion || appVersion}
                  </p>
                  {updateAvailable && latestVersion && (
                    <span className="text-sm text-muted-foreground">
                      → {latestVersion} available
                    </span>
                  )}
                </div>
                {updateAvailable && releaseNotes && (
                  <div className="text-sm text-muted-foreground bg-muted p-2 rounded">
                    <strong>Release Notes:</strong> {releaseNotes}
                  </div>
                )}
              </div>
              <Button
                variant={updateAvailable ? "default" : "outline"}
                size="sm"
                onClick={() => checkForUpdates(true)}
                disabled={isChecking}
              >
                {isChecking ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Checking...
                  </>
                ) : updateAvailable ? (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Update Available
                  </>
                ) : (
                  "Check for Updates"
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {autoUpdate
                ? `Updates will be checked automatically on startup (${
                    betaUpdates ? "beta" : "stable"
                  } channel)`
                : "Enable automatic updates to receive updates automatically"}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* About Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info className="h-5 w-5" />
            About
          </CardTitle>
          <CardDescription>Application and system information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs text-muted-foreground">Version</Label>
              <p className="font-mono">{appVersion}</p>
            </div>
            {platformInfo && (
              <>
                <div>
                  <Label className="text-xs text-muted-foreground">
                    Platform
                  </Label>
                  <p className="font-mono">{platformInfo.os}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">
                    Architecture
                  </Label>
                  <p className="font-mono">{platformInfo.arch}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">
                    Family
                  </Label>
                  <p className="font-mono">{platformInfo.family}</p>
                </div>
              </>
            )}
          </div>

          <div className="pt-2 border-t">
            <p className="text-sm text-muted-foreground">
              © 2025 Lotsgon & FM Skin Builder
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
