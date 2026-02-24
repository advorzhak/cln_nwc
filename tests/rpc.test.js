const {
  executeLightningCommand,
  isCommandAvailable,
  getLightningCliCommand,
} = require("./utils");

// Use configurable lightning-cli command
// Can be overridden with LIGHTNING_DIR_L1 environment variable
const baseCliCommand = getLightningCliCommand(1);

// Check if lightning-cli is available
let lightningCliAvailable = null;

async function checkLightningCli() {
  if (lightningCliAvailable === null) {
    lightningCliAvailable = await isCommandAvailable("lightning-cli");
    if (!lightningCliAvailable) {
      console.warn(
        "\n⚠️  Core Lightning (lightning-cli) not found. Skipping RPC tests.\n" +
          "   Install Core Lightning to run these tests: https://github.com/ElementsProject/lightning\n",
      );
    }
  }
  return lightningCliAvailable;
}

describe("RPC tests", () => {
  describe("nwc-create", () => {
    it("should return an nwc url", async () => {
      const available = await checkLightningCli();
      if (!available) {
        console.log("⏭️  Skipping test - Core Lightning not available");
        return;
      }

      const result = await executeLightningCommand(
        "nwc-create",
        {},
        baseCliCommand,
      );
      expect(result).toHaveProperty("url");
    });

    it("should accept expiry_unix and budget_msat arguments", async () => {
      const available = await checkLightningCli();
      if (!available) {
        console.log("⏭️  Skipping test - Core Lightning not available");
        return;
      }

      const result = await executeLightningCommand(
        "nwc-create",
        {
          expiry_unix: 1000000000,
          budget_msat: 1000000,
        },
        baseCliCommand,
      );
      expect(result).toHaveProperty("url");
    });
  });
});
