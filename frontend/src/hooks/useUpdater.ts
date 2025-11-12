import { useCallback, useEffect, useState } from 'react';
import { check } from '@tauri-apps/plugin-updater';
import { ask, message } from '@tauri-apps/plugin-dialog';
import { relaunch } from '@tauri-apps/plugin-process';

type UpdaterOptions = {
  autoUpdate: boolean;
  betaUpdates: boolean;
};

export function useUpdater({ autoUpdate, betaUpdates }: UpdaterOptions) {
  const [isChecking, setIsChecking] = useState(false);
  const [updateAvailable, setUpdateAvailable] = useState(false);

  const checkForUpdates = useCallback(async (showNoUpdateMessage = false) => {
    setIsChecking(true);
    console.log('[UPDATER] Checking for updates...');
    console.log('[UPDATER] Beta updates:', betaUpdates);

    try {
      const update = await check();

      if (update) {
        console.log('[UPDATER] Update available:', update.version);
        setUpdateAvailable(true);

        const confirmed = await ask(
          `A new version ${update.version} is available!\n\nCurrent version: ${update.currentVersion}\n\nWould you like to download and install it now?`,
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

          // Download and install the update
          await update.downloadAndInstall();

          console.log('[UPDATER] Update installed, relaunching app...');

          // Relaunch the app
          await relaunch();
        } else {
          console.log('[UPDATER] User cancelled update');
        }
      } else {
        console.log('[UPDATER] No updates available');
        setUpdateAvailable(false);

        if (showNoUpdateMessage) {
          await message('You are running the latest version!', {
            title: 'No Updates Available',
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
  }, [betaUpdates]);

  // Check for updates on mount if auto-update is enabled
  useEffect(() => {
    if (autoUpdate) {
      console.log('[UPDATER] Auto-update enabled, checking for updates on startup...');
      // Small delay to let the app initialize
      const timer = setTimeout(() => {
        checkForUpdates(false);
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [autoUpdate, checkForUpdates]);

  return {
    isChecking,
    updateAvailable,
    checkForUpdates,
  };
}
