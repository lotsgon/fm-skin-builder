import { useCallback, useEffect, useState } from 'react';
import { ask, message } from '@tauri-apps/plugin-dialog';
import { relaunch } from '@tauri-apps/plugin-process';
import { getVersion } from '@tauri-apps/api/app';
import { invoke } from '@tauri-apps/api/core';

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
  const [releaseNotes, setReleaseNotes] = useState<string>('');

  // Get current app version
  useEffect(() => {
    getVersion().then(setCurrentVersion).catch(console.error);
  }, []);

  const compareVersions = (current: string, latest: string): number => {
    const currentParts = current.replace(/^v/, '').split('.').map(Number);
    const latestParts = latest.replace(/^v/, '').split('.').map(Number);

    for (let i = 0; i < Math.max(currentParts.length, latestParts.length); i++) {
      const currentPart = currentParts[i] || 0;
      const latestPart = latestParts[i] || 0;

      if (currentPart < latestPart) return -1;
      if (currentPart > latestPart) return 1;
    }

    return 0;
  };

  const checkForUpdates = useCallback(async (showNoUpdateMessage = false) => {
    setIsChecking(true);
    console.log('[UPDATER] Checking for updates...');
    console.log('[UPDATER] Beta updates:', betaUpdates);

    try {
      const endpoint = betaUpdates
        ? 'https://release.fmskinbuilder.com/latest-beta.json'
        : 'https://release.fmskinbuilder.com/latest.json';

      console.log('[UPDATER] Fetching from:', endpoint);

      const response = await fetch(endpoint, {
        headers: {
          'Cache-Control': 'no-cache',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const metadata: ReleaseMetadata = await response.json();
      console.log('[UPDATER] Metadata received:', metadata);

      setLatestVersion(metadata.version);
      setReleaseNotes(metadata.notes);

      if (!currentVersion) {
        console.log('[UPDATER] Current version not available yet');
        return;
      }

      const comparison = compareVersions(currentVersion, metadata.version);

      if (comparison < 0) {
        console.log('[UPDATER] Update available:', metadata.version);
        setUpdateAvailable(true);

        const channel = betaUpdates ? 'beta' : 'stable';
        const confirmed = await ask(
          `A new ${channel} version ${metadata.version} is available!\n\nCurrent version: ${currentVersion}\n\n${metadata.notes ? `Release notes:\n${metadata.notes}\n\n` : ''}Would you like to download and install it now?`,
          {
            title: 'Update Available',
            kind: 'info',
          }
        );

        if (confirmed) {
          console.log('[UPDATER] User confirmed update, downloading...');

          await message('Downloading update... The app will restart when complete.', {
            title: 'Downloading Update',
            kind: 'info',
          });

          // Use Tauri command to download and install update
          try {
            await invoke('download_and_install_update', {
              metadata,
              channel,
            });

            console.log('[UPDATER] Update installed, relaunching app...');

            // Relaunch the app
            await relaunch();
          } catch (installError) {
            console.error('[UPDATER] Installation failed:', installError);
            await message(`Failed to install update: ${String(installError)}`, {
              title: 'Installation Failed',
              kind: 'error',
            });
          }
        } else {
          console.log('[UPDATER] User cancelled update');
        }
      } else if (comparison === 0) {
        console.log('[UPDATER] Already on latest version');
        setUpdateAvailable(false);

        if (showNoUpdateMessage) {
          await message('You are running the latest version!', {
            title: 'No Updates Available',
            kind: 'info',
          });
        }
      } else {
        console.log('[UPDATER] Current version is newer than latest (beta scenario)');
        setUpdateAvailable(false);

        if (showNoUpdateMessage) {
          await message('You are running a version newer than the latest release!', {
            title: 'Development Version',
            kind: 'info',
          });
        }
      }
    } catch (error) {
      console.error('[UPDATER] Error checking for updates:', error);

      if (showNoUpdateMessage) {
        await message(`Failed to check for updates: ${String(error)}`, {
          title: 'Update Check Failed',
          kind: 'error',
        });
      }
    } finally {
      setIsChecking(false);
    }
  }, [betaUpdates, currentVersion]);

  // Check for updates on mount if auto-update is enabled
  useEffect(() => {
    if (autoUpdate && currentVersion) {
      console.log('[UPDATER] Auto-update enabled, checking for updates on startup...');
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
