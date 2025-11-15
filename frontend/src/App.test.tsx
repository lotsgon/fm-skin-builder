import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider } from "@/components/theme-provider";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(() => Promise.resolve(() => {})),
}));

async function renderApp() {
  const module = await import("./App");
  const App = module.default;
  return render(
    <ThemeProvider
      defaultTheme="dark"
      storageKey="fm-skin-builder-ui-theme-test"
    >
      <App />
    </ThemeProvider>
  );
}

describe("App shell", () => {
  beforeEach(() => {
    vi.resetModules();
    invokeMock.mockReset();
    Reflect.deleteProperty(
      window as unknown as Record<string, unknown>,
      "__TAURI_IPC__"
    );
    Reflect.deleteProperty(
      window as unknown as Record<string, unknown>,
      "__TAURI__"
    );
  });

  afterEach(() => {
    cleanup();
  });

  it("informs the user when the backend runtime is missing", async () => {
    invokeMock.mockRejectedValue(new Error("Runtime missing"));
    const user = userEvent.setup();
    await renderApp();

    expect(
      screen.getByText(/(Frontend Preview|Detecting Runtime)/i)
    ).toBeInTheDocument();

    // Set valid paths
    const skinInput = screen.getByLabelText(/Skin Folder/i);
    await user.clear(skinInput);
    await user.type(skinInput, "/tmp/test_skin");

    const bundlesInput = screen.getByLabelText(/Bundles Directory/i);
    await user.clear(bundlesInput);
    await user.type(bundlesInput, "/tmp/bundles");

    // Wait for buttons to become enabled after initialization
    await waitFor(() => {
      const previewButton = screen.getByRole("button", { name: /Preview Build/i });
      expect(previewButton).toBeInTheDocument();
      expect(previewButton).not.toBeDisabled();
    });

    await user.click(screen.getByRole("button", { name: /Preview Build/i }));

    // Check if invoke was called
    expect(invokeMock).toHaveBeenCalled();

    await waitFor(() => {
      expect(
        screen.getByText(/✗ Command failed: Error: Runtime missing/i)
      ).toBeInTheDocument();
    });
  });

  it("sends the correct payload when running in Tauri", async () => {
    Object.defineProperty(window, "__TAURI__", {
      value: { invoke: vi.fn() },
      configurable: true,
    });

    invokeMock.mockResolvedValue({
      stdout: "Patched bundles successfully",
      stderr: "",
      status: 0,
    });

    const user = userEvent.setup();
    await renderApp();

    // Wait for buttons to become enabled after initialization
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Build Bundles/i })
      ).toBeInTheDocument();
    });

    const skinInput = screen.getByLabelText(/Skin Folder/i);
    await user.clear(skinInput);
    await user.type(skinInput, "skins/pro");

    const bundlesInput = screen.getByLabelText(/Bundles Directory/i);
    await user.clear(bundlesInput);
    await user.type(bundlesInput, "/tmp/bundles");

    const debugToggle = screen.getByLabelText(/debug mode/i);
    await user.click(debugToggle);

    await user.click(screen.getByRole("button", { name: /Build Bundles/i }));

    await waitFor(() => {
      expect(invokeMock).toHaveBeenCalledWith("run_python_task", {
        config: {
          skinPath: "skins/pro",
          bundlesPath: "/tmp/bundles",
          debugExport: true,
          dryRun: false,
        },
      });
    });

    await waitFor(() => {
      expect(
        screen.getByText(/Patched bundles successfully/i)
      ).toBeInTheDocument();
    });
  });
});
