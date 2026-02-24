const { exec } = require("child_process");
const path = require("path");

/**
 * Check if a command is available in the system
 *
 * @param {string} command - The command to check
 * @returns {Promise<boolean>} - True if command exists, false otherwise
 */
function isCommandAvailable(command) {
  return new Promise((resolve) => {
    const checkCmd =
      process.platform === "win32" ? `where ${command}` : `which ${command}`;
    exec(checkCmd, (error) => {
      resolve(!error);
    });
  });
}

/**
 * Get the base CLI command for a lightning node
 *
 * @param {number} nodeId - The node number (1, 2, etc.)
 * @returns {string} - The base lightning-cli command
 */
function getLightningCliCommand(nodeId) {
  // Try to use environment variable first
  const lightningDir = process.env[`LIGHTNING_DIR_L${nodeId}`];

  if (lightningDir) {
    return `lightning-cli --lightning-dir=${lightningDir}`;
  }

  // Fallback to default path in temp directory
  const defaultDir = path.join(process.cwd(), ".lightning_nodes", `l${nodeId}`);
  return `lightning-cli --lightning-dir=${defaultDir}`;
}

/**
 * Executes a lightning-cli command with the specified method and arguments.
 *
 * @param {string} method - The RPC method to call (e.g., 'getinfo').
 * @param {Object} args - An object containing the arguments for the method.
 * @param {string} baseCliCommand - Optional base CLI command. If not provided, uses lightning-cli from PATH
 */
function executeLightningCommand(
  method,
  args = {},
  baseCliCommand = "lightning-cli",
) {
  // Construct the arguments string from the args object
  const argsString = Object.keys(args)
    .map((key) => `${key}=${args[key]}`)
    .join(" ");

  const command = `${baseCliCommand} -k ${method} ${argsString || ""}`;

  // console.log(`Executing command: ${command}`)

  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) {
        reject(`exec error: ${error}`);
      }
      if (stderr) {
        reject(`stderr: ${stderr}`);
      }

      try {
        // Handle empty stdout
        if (!stdout || stdout.trim() === "") {
          reject(`stderr: Command returned empty output`);
          return;
        }
        const result = JSON.parse(stdout);
        resolve(result);
      } catch (parseError) {
        console.error(`Error parsing JSON output: ${parseError}`);
        console.error(`stdout was: ${stdout}`);
        reject(`stdout: ${stdout}`);
      }
    });
  });
}

function generateRandomString(length = 10) {
  const characters =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let result = "";
  const charactersLength = characters.length;
  for (let i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
  }
  return result;
}

module.exports = {
  executeLightningCommand,
  generateRandomString,
  isCommandAvailable,
  getLightningCliCommand,
};
