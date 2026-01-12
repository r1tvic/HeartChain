require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: "../.env" }); // Load from parent .env

const SHARDEUM_RPC = process.env.SHARDEUM_RPC_URL || "https://api-mezame.shardeum.org/";
const PRIVATE_KEY = process.env.ADMIN_PRIVATE_KEY;

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
    solidity: "0.8.19",
    networks: {
        shardeum: {
            url: SHARDEUM_RPC,
            accounts: PRIVATE_KEY ? [PRIVATE_KEY] : [],
            chainId: 8119,
        },
        hardhat: {
            // Local testing
        }
    },
    paths: {
        sources: "./contracts",
        tests: "./test",
        cache: "./cache",
        artifacts: "./artifacts"
    }
};
