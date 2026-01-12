const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    console.log("🚀 Starting deployment to Shardeum...");

    if (!process.env.ADMIN_PRIVATE_KEY) {
        throw new Error("ADMIN_PRIVATE_KEY not found in .env");
    }

    // Deploy
    const HeartChain = await hre.ethers.getContractFactory("HeartChain");
    const heartChain = await HeartChain.deploy();

    console.log("Waiting for deployment...");
    await heartChain.waitForDeployment();

    const address = await heartChain.getAddress();
    console.log(`✅ HeartChain deployed to: ${address}`);

    // Instructions for User
    console.log("\n IMPORTANT: Update your .env file in the root directory with:");
    console.log(`CONTRACT_ADDRESS=${address}`);

    // Optional: Auto-update helper (commented out for safety)
    // updateEnvFile(address);
}

function updateEnvFile(address) {
    const envPath = path.join(__dirname, "../../.env");
    const envContent = fs.readFileSync(envPath, "utf8");
    const newContent = envContent.includes("CONTRACT_ADDRESS=")
        ? envContent.replace(/CONTRACT_ADDRESS=.*/, `CONTRACT_ADDRESS=${address}`)
        : envContent + `\nCONTRACT_ADDRESS=${address}`;

    fs.writeFileSync(envPath, newContent);
    console.log("Updated .env file successfully.");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
