/// <reference types="vite/client" />
/* eslint-disable no-unused-vars */

type TauriBridge = {
  invoke?: (...args: unknown[]) => Promise<unknown>;
  [key: string]: unknown;
};

declare global {
  interface Window {
    __TAURI_IPC__?: unknown;
    __TAURI__?: TauriBridge;
  }
}

export {};
