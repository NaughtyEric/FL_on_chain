require("@nomicfoundation/hardhat-toolbox");

/** @type import("hardhat/config").HardhatUserConfig */
module.exports = {
  solidity: "0.8.20",
  networks: {
    // 本地测试链：`npx hardhat node` 启动，默认 127.0.0.1:8545（链 ID 31337）
    localhost: {
      url: "http://127.0.0.1:8545",
    },
  },
};
