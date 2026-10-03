// 部署 L1 账本 + L2 聚合层（L2 构造时注入 L1 地址），并把 L2FL 登记为 L1 上的 L2 角色。
// 本地测试链用法：`bash scripts/chain/start_chain.sh` 后 `npx hardhat run scripts/deploy.js --network localhost`
//
// L1 乐观落账参数（可用环境变量覆盖）：
//   L1_CHALLENGE_PERIOD  挑战窗口秒数（默认 86400 = 1 天；本地调试可设小，如 60）
//   L1_COMMIT_BOND       提交押金，单位 ether（默认 1）
//   L1_CHALLENGE_BOND    挑战押金，单位 ether（默认 0.5）
const hre = require("hardhat");

const ROLE_L2 = 3; // L1FL.Role { NONE, CLIENT, SERVER, L2 }

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deployer:", deployer.address);

  const challengePeriod = BigInt(process.env.L1_CHALLENGE_PERIOD ?? 24 * 3600);
  const commitBond = hre.ethers.parseEther(process.env.L1_COMMIT_BOND ?? "1");
  const challengeBond = hre.ethers.parseEther(process.env.L1_CHALLENGE_BOND ?? "0.5");

  // 1. L1 账本（挑战窗口 + 两种押金在构造时固定为 immutable）
  const L1FL = await hre.ethers.getContractFactory("L1FL");
  const l1 = await L1FL.deploy(challengePeriod, commitBond, challengeBond);
  await l1.waitForDeployment();
  const l1Address = await l1.getAddress();
  console.log("L1FL deployed at:", l1Address);
  console.log(`  challengePeriod=${challengePeriod}s commitBond=${hre.ethers.formatEther(commitBond)} ETH ` +
              `challengeBond=${hre.ethers.formatEther(challengeBond)} ETH`);

  // 2. L2 聚合层（注入 L1 地址）
  const L2FL = await hre.ethers.getContractFactory("L2FL");
  const l2 = await L2FL.deploy(l1Address);
  await l2.waitForDeployment();
  const l2Address = await l2.getAddress();
  console.log("L2FL deployed at:", l2Address);
  console.log("L2FL.l1 ->", await l2.l1());

  // 3. 把 L2FL 登记为 L1 上唯一有权 commitRound 的 L2 角色（L2FL.commitToL1 尚未实现，
  //    本地手工调试可另行 `l1.registerParticipant(<EOA>, 3)` 登记一个外部账户）。
  await (await l1.registerParticipant(l2Address, ROLE_L2)).wait();
  console.log("L1FL.registerParticipant(L2FL, L2) done");

  console.log("部署完成。L1 提交/挑战/确定流程已可用；L2 的 distribute/analyze/commitToL1 与 L1 payReward 仍为 NotImplemented 占位");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
