// Increase timeout for slow machines or CI environments
const baseTimeout = 30000;
const slowMachineMultiplier = process.env.SLOW_MACHINE ? 3 : 1;
const testTimeout = baseTimeout * slowMachineMultiplier;

module.exports = {
  testEnvironment: "node",
  testTimeout: testTimeout,
  forceExit: true,
  detectOpenHandles: false,
  testMatch: ["**/*.test.js"],
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
};
