const {defineConfig} = require("@playwright/test")

module.exports = defineConfig({
    testDir: "./browser-tests",
    fullyParallel: true,
    reporter: "line",
    use: {
        channel: "chrome",
        headless: true,
    },
})
