// 部署 L1 账本 + L2 聚合层（L2 构造时注入 L1 地址）。
// 本地测试链用法：`npx hardhat node` 后另开终端 `npx hardhat run scripts/deploy.js --network localhost`
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer:", deployer.address);

  // 1. L1 账本（无构造参数）
  const L1FL = await hre.ethers.getContractFactory("L1FL");
  const l1 = await L1FL.deploy();
  await l1.waitForDeployment();
  const l1Address = await l1.getAddress();
  console.log("L1FL deployed at:", l1Address);

  // 2. L2 聚合层（注入 L1 地址）
  const L2FL = await hre.ethers.getContractFactory("L2FL");
  const l2 = await L2FL.deploy(l1Address);
  await l2.waitForDeployment();
  const l2Address = await l2.getAddress();
  console.log("L2FL deployed at:", l2Address);
  console.log("L2FL.l1 ->", await l2.l1());

  console.log("部署完成（当前均为框架占位，调用业务函数将 revert NotImplemented）");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
