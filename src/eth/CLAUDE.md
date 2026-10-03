# eth

FL 链上账本合约。

- **L2FL** 已实现：参与方申请（`applyToJoin`，申请即自动 APPROVED）、上传参数 id（`uploadParameters`）、按 id 查询（`getByParamId`）。`distributeParameters`/`analyzeAndAggregate`/`commitToL1` 仍为 `revert NotImplemented()` 占位。
- **L1FL** 已实现乐观落账生命周期：`registerParticipant`（owner 登记角色）→ `commitRound`（仅 L2 角色，押 `commitBond`，进入 PENDING + 挑战窗口）→ `challenge`（任何人，押 `challengeBond`，→ CHALLENGED）→ `resolveChallenge(upheld)`（owner 仲裁：成立 → REJECTED、两押金归挑战者；驳回 → 回 PENDING、挑战押金归提交方）→ `finalizeRound`（无权限，窗口过后 → FINALIZED，退还提交押金，更新 `latestRound`）。押金/奖励经 `pendingWithdrawals` + `withdraw()` pull 提取。`payReward` 仍为占位。
- `contracts/L1FL.sol` · `contracts/L2FL.sol` · `interfaces/IL1FL.sol`（`RoundStatus`/`RoundRecord`，`commitRound` 为 payable）· `test/fl-flow.js`（框架冒烟）· `test/l1-round-lifecycle.js`（L1 生命周期）· `scripts/deploy.js`

```text
npx hardhat compile | test | node          # node: 127.0.0.1:8545, chainId 31337
L1_CHALLENGE_PERIOD=60 npx hardhat run scripts/deploy.js --network localhost   # 部署并把 L2FL 登记为 L2 角色
```

## 约定

- 参数 id 来自链下 `scripts/storage/` 的 sha256（对应 DCMF-BFL 论文的 CID）；大对象永不上链。
- 时间戳（`uploadedAt`/`committedAt`/`finalizeAfter`）一律由 `block.timestamp` 共识赋值，不接受调用方传入。
- `challengePeriod`/`commitBond`/`challengeBond` 为构造期 `immutable`，押金金额必须精确匹配（`WrongBond`）。
- `resolveChallenge` 由 owner 仲裁是**明确的信任占位**：这是链上欺诈证明（交互式二分 / ZK verifier）的插入点，替换时保持状态机与押金结算语义不变。
- 被 REJECTED 的轮次为终态，同一轮号不可重新提交；轮次之间无父子依赖（父子链接留待 ZKP 设计）。
- 未实现函数保持 `revert NotImplemented()` 占位，不写空实现。
- 合约由 off-chain `src/python` Flower 客户端/服务端驱动（集成未实现）。
