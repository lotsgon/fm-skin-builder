import { useCallback, useEffect, useState } from "react";
import { ask, message } from "@tauri-apps/plugin-dialog";
import { relaunch } from "@tauri-apps/plugin-process";
import { getVersion } from "@tauri-apps/api/app";
import { fetch } from "@tauri-apps/plugin-http";
import { invoke } from "@tauri-apps/api/core";

type UpdaterOptions = {
  autoUpdate: boolean;
  betaUpdates: boolean;
};

type ReleaseMetadata = {
  version: string;
  pub_date: string;
  platforms: Record<string, any>;
  notes: string;
};

export function useUpdater({ autoUpdate, betaUpdates }: UpdaterOptions) {
  const [isChecking, setIsChecking] = useState(false);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [latestVersion, setLatestVersion] = useState<string | null>(null);
  const [currentVersion, setCurrentVersion] = useState<string | null>(null);
  const [releaseNotes, setReleaseNotes] = useState<string>("");

  // Get current app version
  useEffect(() => {
    getVersion().then(setCurrentVersion).catch(console.error);
  }, []);

  const compareVersions = (current: string, latest: string): number => {
    // Handle semantic versions with pre-release identifiers
    const parseVersion = (version: string): (number | string)[] => {
      return version
        .replace(/^v/, "") // Remove leading 'v'
        .split(/[.-]/) // Split on dots and dashes
        .map((part) => {
          const num = parseInt(part, 10);
          return isNaN(num) ? part : num;
        });
    };

    const currentParts = parseVersion(current);
    const latestParts = parseVersion(latest);

    console.log("[UPDATER] Parsed versions:", {
      current: currentParts,
      latest: latestParts,
    });

    for (
      let i = 0;
      i < Math.max(currentParts.length, latestParts.length);
      i++
    ) {
      const currentPart = currentParts[i];
      const latestPart = latestParts[i];

      // Handle undefined parts (shorter version strings)
      if (currentPart === undefined && latestPart === undefined) continue;
      if (currentPart === undefined) return -1; // Shorter version is smaller
      if (latestPart === undefined) return 1; // Shorter version is smaller

      // Compare numbers
      if (typeof currentPart === "number" && typeof latestPart === "number") {
        if (currentPart < latestPart) return -1;
        if (currentPart > latestPart) return 1;
      }
      // Compare strings (pre-release identifiers)
      else if (
        typeof currentPart === "string" &&
        typeof latestPart === "string"
      ) {
        const cmp = currentPart.localeCompare(latestPart);
        if (cmp !== 0) return cmp < 0 ? -1 : 1;
      }
      // Mixed types: numbers come before strings in semantic versioning
      else {
        if (typeof currentPart === "number") return -1;
        if (typeof latestPart === "number") return 1;
      }
    }

    return 0;
  };

  const checkForUpdates = useCallback(
    async (showNoUpdateMessage = false) => {
      setIsChecking(true);
      console.log("[UPDATER] Checking for updates...");
      console.log("[UPDATER] Beta updates:", betaUpdates);
      console.log("[UPDATER] Current version:", currentVersion);

      try {
        const endpoint = betaUpdates
          ? "https://release.fmskinbuilder.com/latest-beta.json"
          : "https://release.fmskinbuilder.com/latest.json";

        console.log("[UPDATER] Fetching from:", endpoint);

        const response = await fetch(endpoint, {
          method: "GET",
          headers: {
            "Cache-Control": "no-cache",
          },
        });

        console.log("[UPDATER] Response status:", response.status);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const metadata: ReleaseMetadata = await response.json();
        console.log("[UPDATER] Metadata received:", metadata);
        console.log(
          "[UPDATER] Latest version from metadata:",
          metadata.version
        );

        setLatestVersion(metadata.version);
        setReleaseNotes(metadata.notes);

        if (!currentVersion) {
          console.log("[UPDATER] Current version not available yet");
          return;
        }

        const comparison = compareVersions(currentVersion, metadata.version);
        console.log(
          "[UPDATER] Version comparison result:",
          comparison,
          `(current: ${currentVersion}, latest: ${metadata.version})`
        );

        if (comparison < 0) {
          console.log("[UPDATER] Update available:", metadata.version);
          setUpdateAvailable(true);

          const channel = betaUpdates ? "beta" : "stable";
          const confirmed = await ask(
            `A new ${channel} version ${
              metadata.version
            } is available!\n\nCurrent version: ${currentVersion}\n\n${
              metadata.notes ? `Release notes:\n${metadata.notes}\n\n` : ""
            }Would you like to download and install it now?`,
            {
              title: "Update Available",
              kind: "info",
            }
          );

          if (confirmed) {
            console.log("[UPDATER] User confirmed update, downloading...");

            await message(
              "Downloading update... The app will restart when complete.",
              {
                title: "Downloading Update",
                kind: "info",
              }
            );

            // Use Tauri command to download and install update
            try {
              await invoke("download_and_install_update", {
                metadata,
                channel,
              });

              console.log("[UPDATER] Update installed, relaunching app...");

              // Relaunch the app
              await relaunch();
            } catch (installError) {
              console.error("[UPDATER] Installation failed:", installError);
              await message(
                `Failed to install update: ${String(installError)}`,
                {
                  title: "Installation Failed",
                  kind: "error",
                }
              );
            }
          } else {
            console.log("[UPDATER] User cancelled update");
          }
        } else if (comparison === 0) {
          console.log("[UPDATER] Already on latest version");
          setUpdateAvailable(false);

          if (showNoUpdateMessage) {
            await message("You are running the latest version!", {
              title: "No Updates Available",
              kind: "info",
            });
          }
        } else {
          console.log(
            "[UPDATER] Current version is newer than latest (development scenario)"
          );
          setUpdateAvailable(false);

          if (showNoUpdateMessage) {
            await message(
              "You are running a version newer than the latest release!",
              {
                title: "Development Version",
                kind: "info",
              }
            );
          }
        }
      } catch (error) {
        console.error("[UPDATER] Error checking for updates:", error);
        console.error("[UPDATER] Error details:", {
          message: error.message,
          stack: error.stack,
          name: error.name,
        });

        if (showNoUpdateMessage) {
          await message(`Failed to check for updates: ${String(error)}`, {
            title: "Update Check Failed",
            kind: "error",
          });
        }
      } finally {
        setIsChecking(false);
      }
    },
    [betaUpdates, currentVersion]
  );

  // Check for updates on mount if auto-update is enabled
  useEffect(() => {
    if (autoUpdate && currentVersion) {
      console.log(
        "[UPDATER] Auto-update enabled, checking for updates on startup..."
      );
      // Small delay to let the app initialize
      const timer = setTimeout(() => {
        checkForUpdates(false);
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [autoUpdate, checkForUpdates, currentVersion]);

  return {
    isChecking,
    updateAvailable,
    latestVersion,
    currentVersion,
    releaseNotes,
    checkForUpdates,
  };
}
