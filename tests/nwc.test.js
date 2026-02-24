const {
  executeLightningCommand,
  generateRandomString,
  getLightningCliCommand,
  isCommandAvailable,
} = require("./utils");
const { webln } = require("@getalby/sdk");
const crypto = require("crypto");
const WebSocket = require("ws");

globalThis.WebSocket = WebSocket;
globalThis.crypto = crypto;

// Use configurable lightning-cli commands
const l1 = getLightningCliCommand(1);
const l2 = getLightningCliCommand(2);

let nwc = null;
let nwcEnabled = null;
let nwcConnection = null;
let lightningCliAvailable = null;

async function setupNWCConnection() {
  if (nwcConnection === null) {
    // Check if lightning-cli is available
    if (lightningCliAvailable === null) {
      lightningCliAvailable = await isCommandAvailable("lightning-cli");
      if (!lightningCliAvailable) {
        console.warn(
          "\n⚠️  Core Lightning (lightning-cli) not found. Skipping NWC tests.\n" +
            "   Install Core Lightning to run these tests: https://github.com/ElementsProject/lightning\n",
        );
        nwcConnection = false;
        return false;
      }
    }

    try {
      // Create a new NWC connection on l1
      console.log("Creating NWC connection on l1...");
      nwcConnection = await executeLightningCommand("nwc-create", {}, l1);
      console.log("✅ NWC connection created:", nwcConnection.url);

      // Initialize the NWC provider with the created connection
      nwc = new webln.NostrWebLNProvider({
        nostrWalletConnectUrl: nwcConnection.url,
      });
    } catch (error) {
      console.error("Failed to create NWC connection:", error);
      nwcConnection = false;
    }
  }
  return nwcConnection !== false;
}

async function checkNWCConnection() {
  if (nwcEnabled === null) {
    // First, ensure we have a connection
    const hasConnection = await setupNWCConnection();
    if (!hasConnection) {
      nwcEnabled = false;
      console.warn("\n⚠️  Failed to setup NWC connection.\n");
      return false;
    }

    try {
      // Set a timeout for the initial connection attempt
      // Use longer timeout on slow machines or CI environments
      const timeoutMs = process.env.SLOW_MACHINE ? 15000 : 5000;
      const enablePromise = nwc.enable();
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(
          () => reject(new Error("NWC connection timeout")),
          timeoutMs,
        ),
      );

      await Promise.race([enablePromise, timeoutPromise]);
      nwcEnabled = true;
      console.log("✅ NWC provider connected successfully");
    } catch (error) {
      nwcEnabled = false;
      console.warn(
        "\n⚠️  Failed to enable NWC provider (Nostr relay unavailable).\n" +
          "   Some tests will be skipped. Error: " +
          error.message +
          "\n",
      );
    }
  }
  return nwcEnabled;
}

afterAll(async () => {
  try {
    if (nwcEnabled && nwc && typeof nwc.close === "function") {
      await nwc.close();
    }
    // Clean up the NWC connection
    if (nwcConnection && nwcConnection.pubkey) {
      console.log("Cleaning up NWC connection...");
      await executeLightningCommand(
        "nwc-delete",
        { pubkey: nwcConnection.pubkey },
        l1,
      );
    }
  } catch (error) {
    console.warn("Error during cleanup:", error.message);
  }
});

describe("pay_invoice", () => {
  it("should pay an invoice", async () => {
    const connected = await checkNWCConnection();
    if (!connected) {
      console.log("⏭️  Skipping test - NWC provider not available");
      return;
    }

    try {
      const randomString = generateRandomString();
      const l2Invoice = await executeLightningCommand(
        "invoice",
        {
          amount_msat: 10000,
          label: randomString,
          description: "descritption",
        },
        l2,
      );
      if (!l2Invoice.bolt11) {
        throw new Error("Failed to create invoice");
      }
      const result = await nwc.sendPayment(l2Invoice.bolt11);
      expect(result).toHaveProperty("preimage");
    } catch (error) {
      // Skip test if we encounter known Core Lightning issues
      if (
        error.error &&
        (error.error.includes("deprecated") ||
          error.error.includes("Ran out of routes"))
      ) {
        console.warn(
          `⏭️  Skipping test due to Core Lightning issue: ${error.error}`,
        );
        return;
      }
      throw error;
    }
  });
});

describe("make_invoice", () => {
  it("should make an invoice", async () => {
    const connected = await checkNWCConnection();
    if (!connected) {
      console.log("⏭️  Skipping test - NWC provider not available");
      return;
    }

    const result = await nwc.makeInvoice({
      amount: 10000,
      description: generateRandomString(),
    });

    expect(result).toHaveProperty("paymentRequest");
  });
});

describe("get_info", () => {
  it("should return the nwc info", async () => {
    const connected = await checkNWCConnection();
    if (!connected) {
      console.log("⏭️  Skipping test - NWC provider not available");
      return;
    }

    const result = await nwc.getInfo();
    expect(result).toMatchObject({
      node: expect.anything(),
      version: expect.any(String),
      supports: expect.anything(),
      methods: expect.anything(),
    });
  });
});

describe("pay_keysend", () => {
  it("should pay a node via keysend", async () => {
    const connected = await checkNWCConnection();
    if (!connected) {
      console.log("⏭️  Skipping test - NWC provider not available");
      return;
    }

    try {
      const destination = await executeLightningCommand("getinfo", {}, l2);
      const result = await nwc.keysend({
        destination: destination.id,
        amount: 10000,
      });

      expect(result).toHaveProperty("preimage");
    } catch (error) {
      // Skip test if we encounter known Core Lightning issues
      if (
        error.error &&
        (error.error.includes("deprecated") ||
          error.error.includes("Ran out of routes"))
      ) {
        console.warn(
          `⏭️  Skipping test due to Core Lightning issue: ${error.error}`,
        );
        return;
      }
      throw error;
    }
  });
});

describe("get_balance", () => {
  it("should return the node's balance", async () => {
    const connected = await checkNWCConnection();
    if (!connected) {
      console.log("⏭️  Skipping test - NWC provider not available");
      return;
    }

    const balance = await nwc.getBalance();

    expect(balance).toMatchObject({
      balance: expect.any(Number),
      currency: "sats",
    });
  });
});

// describe("list_transactions", () => {
//   it("should return a list of transaction", async () => {
//     const result = await nwc.listTransactions();
//     expect(result).toEqual(
//       expect.arrayContaining([
//         expect.objectContaining({
//           type: expect.any(String),
//           invoice: expect.any(String),
//           description: expect.any(String),
//           description_hash: expect.any(String),
//           preimage: expect.any(String),
//           payment_hash: expect.any(String),
//           amount: expect.any(Number),
//           fees_paid: expect.any(Number),
//           settled_at: expect.any(Number),
//           created_at: expect.any(Number),
//           expires_at: expect.any(Number),
//           metadata: expect.any(Object),
//         }),
//       ])
//     );
//   });
// });

// describe("lookup_invoice", () => {
//   it("should return an invoice looked up by payment_hash", async () => {
//     const randomString = generateRandomString();
//     const l2Invoice = await executeLightningCommand(
//       "invoice",
//       { amount_msat: 10000, label: randomString, description: "descritption" },
//       l2
//     );
//     if (!l2Invoice.payment_hash) {
//       throw new Error("Failed to create invoice");
//     }
//     const result = await nwc.lookupInvoice({
//       payment_hash: l2Invoice.payment_hash,
//     });
//     expect(result).toHaveProperty("paymentRequest");
//   });
//   it("should return an invoice looked up by bolt11", async () => {
//     const randomString = generateRandomString();
//     const l2Invoice = await executeLightningCommand(
//       "invoice",
//       { amount_msat: 10000, label: randomString, description: "descritption" },
//       l2
//     );
//     if (!l2Invoice.bolt11) {
//       throw new Error("Failed to create invoice");
//     }
//     const result = await nwc.lookupInvoice({ invoice: l2Invoice.bolt11 });
//     expect(result).toHaveProperty("paymentRequest");
//   });
// });
