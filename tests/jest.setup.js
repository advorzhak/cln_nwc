/**
 * Jest setup file for handling async cleanup
 */

const { spawn, execSync } = require("child_process");
const path = require("path");
const fs = require("fs");
const WebSocket = require("ws");

// Make WebSocket available globally
globalThis.WebSocket = WebSocket;

// Increase timeout for integration tests
// Use longer timeout on slow machines or CI environments
const baseTimeout = 30000;
const slowMachineMultiplier = process.env.SLOW_MACHINE ? 3 : 1;
const timeout = baseTimeout * slowMachineMultiplier;

jest.setTimeout(timeout);

// Start mock relay before tests
let mockRelayProcess = null;

// Helper to wait for relay to be ready
async function waitForRelay(maxRetries = 20, delay = 250) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const ws = new WebSocket("ws://localhost:8001");
      return new Promise((resolve) => {
        ws.onopen = () => {
          ws.close();
          resolve(true);
        };
        ws.onerror = () => {
          resolve(false);
        };
        setTimeout(() => resolve(false), delay);
      });
    } catch (e) {
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
  return false;
}

beforeAll(async () => {
  // Set environment variable flag for plugin
  process.env.TEST_RELAY = "1";

  // Check if relay is already running (e.g., in CI)
  const alreadyRunning = await waitForRelay(2, 100); // Quick check

  if (alreadyRunning) {
    console.log("Mock relay already running, skipping startup");
    return;
  }

  // Start mock relay if not testing in external relay mode
  if (!process.env.EXTERNAL_RELAY) {
    console.log("Starting mock relay...");

    // Determine which Python executable to use
    // Priority: active venv > local venv > system python
    let pythonExe = null;

    // 1. Check if VIRTUAL_ENV is already set (from venv activation)
    if (process.env.VIRTUAL_ENV) {
      pythonExe = path.join(process.env.VIRTUAL_ENV, "bin", "python");
      if (fs.existsSync(pythonExe)) {
        console.log(`Using active venv: ${pythonExe}`);
      } else {
        pythonExe = null;
      }
    }

    // 1b. Check GitHub Actions pythonLocation
    if (!pythonExe && process.env.pythonLocation) {
      const ghPython = path.join(process.env.pythonLocation, "bin", "python");
      if (fs.existsSync(ghPython)) {
        pythonExe = ghPython;
        console.log(`Using GitHub Actions Python: ${pythonExe}`);
      }
    }

    // 2. Check for local .venv
    if (!pythonExe) {
      const venvPython = path.join(__dirname, "..", ".venv", "bin", "python");
      if (fs.existsSync(venvPython)) {
        pythonExe = venvPython;
        console.log(`Using local .venv: ${pythonExe}`);
      }
    }

    // 3. Try common GitHub Actions and system Python locations
    const pythonCandidates = [
      "/opt/hostedtoolcache/Python/3.12.0/x64/bin/python3", // GitHub Actions Python 3.12
      "/opt/hostedtoolcache/Python/3.8.18/x64/bin/python3", // GitHub Actions Python 3.8
      "/usr/bin/python3", // Linux system
      "/usr/local/bin/python3", // macOS
    ];

    if (!pythonExe) {
      for (const candidate of pythonCandidates) {
        if (fs.existsSync(candidate)) {
          pythonExe = candidate;
          console.log(`Found Python at: ${pythonExe}`);
          break;
        }
      }
    }

    // 4. Last resort: try shell PATH
    if (!pythonExe) {
      try {
        const result = execSync("which python3", {
          encoding: "utf-8",
          stdio: ["pipe", "pipe", "ignore"],
        }).trim();
        if (result) {
          pythonExe = result;
          console.log(`Found Python from PATH: ${pythonExe}`);
        }
      } catch (e) {
        // Continue
      }
    }

    if (!pythonExe) {
      throw new Error(
        "Could not find Python executable. Checked: VIRTUAL_ENV, .venv, " +
          "GitHub Actions paths, and system paths.",
      );
    }

    // Prepare environment for child process
    const envCopy = { ...process.env };

    // Ensure PYTHONUNBUFFERED is set for immediate output
    envCopy.PYTHONUNBUFFERED = "1";

    mockRelayProcess = spawn(
      pythonExe,
      [path.join(__dirname, "mock_relay.py")],
      {
        env: envCopy,
        stdio: ["ignore", "pipe", "pipe"], // Don't inherit stdin, but capture stdout/stderr
        detached: false,
        // Don't use cwd - inherit from parent
      },
    );

    if (!mockRelayProcess || !mockRelayProcess.pid) {
      throw new Error("Failed to spawn mock relay process");
    }

    console.log(
      `Mock relay spawned with PID ${mockRelayProcess.pid} using ${pythonExe}`,
    );

    // Log relay output
    mockRelayProcess.stdout.on("data", (data) => {
      console.log(`[MockRelay] ${data.toString().trim()}`);
    });

    mockRelayProcess.stderr.on("data", (data) => {
      console.error(`[MockRelay ERR] ${data.toString().trim()}`);
    });

    mockRelayProcess.on("error", (error) => {
      console.error("Failed to start mock relay:", error);
    });

    mockRelayProcess.on("exit", (code, signal) => {
      console.log(
        `Mock relay exited - PID: ${mockRelayProcess.pid}, code: ${code}, signal: ${signal}`,
      );
    });

    // Give relay a moment to start
    await new Promise((resolve) => setTimeout(resolve, 500));

    // Wait for relay to be ready
    const ready = await waitForRelay(30, 200); // 30 retries × 200ms = 6 seconds
    if (!ready) {
      const isStillRunning = mockRelayProcess && !mockRelayProcess.killed;
      if (!isStillRunning) {
        throw new Error("Mock relay process exited before becoming ready");
      }
      throw new Error(
        "Mock relay failed to start or become ready on ws://localhost:8001",
      );
    }
    console.log("Mock relay is ready!");
  }
});

// Handle uncaught promise rejections
process.on("unhandledRejection", (reason) => {
  console.error("Unhandled Rejection:", reason);
});

// Gracefully close any open handles after tests complete
afterAll(async () => {
  // Kill mock relay only if we started it (not if it was already running)
  if (mockRelayProcess && mockRelayProcess.pid) {
    console.log("Stopping mock relay...");
    mockRelayProcess.kill();
  }

  // Give async operations a moment to complete
  await new Promise((resolve) => setTimeout(resolve, 100));

  // Close any remaining WebSocket connections
  if (globalThis.WebSocket && globalThis.WebSocket.CONNECTING) {
    // Force close any open WebSocket connections
    try {
      // This will catch any lingering WebSocket instances
      const connections = Object.getOwnPropertyNames(globalThis)
        .filter((name) => name.includes("ws"))
        .map((name) => globalThis[name]);

      connections.forEach((conn) => {
        if (conn && typeof conn.close === "function") {
          conn.close();
        }
      });
    } catch (e) {
      // Silently fail if there's nothing to close
    }
  }
});
