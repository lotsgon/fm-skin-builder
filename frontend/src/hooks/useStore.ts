import { useEffect, useState } from 'react';
import { Store } from '@tauri-apps/plugin-store';

export type AppSettings = {
  skinPath?: string;
  bundlesPath?: string;
  betaUpdates?: boolean;
  checkForUpdates?: boolean;
};

let storeInstance: Store | null = null;

async function getStore(): Promise<Store> {
  if (!storeInstance) {
    storeInstance = await Store.load('settings.json', { autoSave: false });
  }
  return storeInstance;
}

export function useStore() {
  const [isLoading, setIsLoading] = useState(true);
  const [settings, setSettings] = useState<AppSettings>({});

  // Load settings on mount
  useEffect(() => {
    async function loadSettings() {
      try {
        const store = await getStore();

        const skinPath = await store.get<string>('skinPath');
        const bundlesPath = await store.get<string>('bundlesPath');
        const betaUpdates = await store.get<boolean>('betaUpdates');
        const checkForUpdates = await store.get<boolean>('checkForUpdates');

        setSettings({
          skinPath: skinPath || undefined,
          bundlesPath: bundlesPath || undefined,
          betaUpdates: betaUpdates ?? false,
          checkForUpdates: checkForUpdates ?? true,
        });
      } catch (error) {
        console.error('Failed to load settings:', error);
      } finally {
        setIsLoading(false);
      }
    }

    loadSettings();
  }, []);

  // Save a single setting
  const saveSetting = async <K extends keyof AppSettings>(
    key: K,
    value: AppSettings[K]
  ): Promise<void> => {
    try {
      const store = await getStore();

      if (value === undefined) {
        await store.delete(key);
      } else {
        await store.set(key, value);
      }

      await store.save();

      setSettings(prev => ({ ...prev, [key]: value }));
    } catch (error) {
      console.error(`Failed to save setting ${String(key)}:`, error);
      throw error;
    }
  };

  // Save multiple settings at once
  const saveSettings = async (newSettings: Partial<AppSettings>): Promise<void> => {
    try {
      const store = await getStore();

      for (const [key, value] of Object.entries(newSettings)) {
        if (value === undefined) {
          await store.delete(key);
        } else {
          await store.set(key, value);
        }
      }

      await store.save();

      setSettings(prev => ({ ...prev, ...newSettings }));
    } catch (error) {
      console.error('Failed to save settings:', error);
      throw error;
    }
  };

  // Clear a single setting
  const clearSetting = async (key: keyof AppSettings): Promise<void> => {
    await saveSetting(key, undefined);
  };

  // Clear all settings
  const clearAllSettings = async (): Promise<void> => {
    try {
      const store = await getStore();
      await store.clear();
      await store.save();

      setSettings({});
    } catch (error) {
      console.error('Failed to clear settings:', error);
      throw error;
    }
  };

  return {
    settings,
    isLoading,
    saveSetting,
    saveSettings,
    clearSetting,
    clearAllSettings,
  };
}
