# eth

以太坊智能合约，联邦学习链上账本框架。**框架阶段**：参与方的申请/上传与按 id 查询已实现（对齐 DCMF-BFL 内容寻址）；聚合、上报 L1 等函数仍为 `revert NotImplemented()` 占位。

## 结构

- `contracts/L1FL.sol` — L1 主链账本：登记参与方、存储 L2 上报的聚合结果、激励占位
- `contracts/L2FL.sol` — L2 聚合层：客户端申请/上传参数 id、服务端下发参数、聚合后上报 L1
- `interfaces/IL1FL.sol` — L1 对 L2 暴露的跨链接口
- `test/fl-flow.js` — 框架冒烟测试
- `scripts/deploy.js` — 部署脚本

## 本地测试链（Hardhat）

```text
npx hardhat compile            # 编译
npx hardhat test               # 跑测试
npx hardhat node               # 起本地测试链（127.0.0.1:8545, chainId 31337）
npx hardhat run scripts/deploy.js --network localhost   # 部署到测试链
```

## 流程（对应函数）

1. 客户端申请 `L2FL.applyToJoin()` ✅ 已实现（申请即自动 APPROVED，正式版改为服务端审批）
2. 服务端给参数 `L2FL.distributeParameters()`（占位）
3. 客户端本地训练（off-chain）
4. 客户端上传到 L2 `L2FL.uploadParameters()` ✅ 已实现
5. L2 分析后上传 L1 `L2FL.analyzeAndAggregate()` → `commitToL1()` → `IL1FL.commitRound()`（占位）

## 约定

- 已实现：`applyToJoin`（客户端自注册）、`uploadParameters`（上传参数 id）+ 内容寻址登记表 `paramRecords` + 查询 `getByParamId`。
  - 参数 id 来自链下内容寻址存储 `scripts/storage/` 的 sha256（对应 DCMF-BFL 论文的 CID）：参与方把更新存到链下得到 id，仅把 id 上链；大对象永不上链。
  - 约束：未申请（NONE）不可上传 → `NotApproved`；`round == 0` → `InvalidRound`；`paramId == bytes32(0)` → `InvalidParamId`；同客户端同轮仅一次 → `AlreadyUploaded`；参数 id 全局唯一 → `ParamIdTaken`。
- 仍未实现：`distributeParameters` / `analyzeAndAggregate` / `commitToL1`（L1FL 全部），函数体以 `revert NotImplemented()` 占位，避免空实现被误调用。
- 本目录合约由 off-chain `src/python` Flower 客户端/服务端配合驱动。
