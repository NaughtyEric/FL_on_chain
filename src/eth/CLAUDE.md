# eth

以太坊智能合约，联邦学习链上账本框架（**未实现**，函数体均为 `revert NotImplemented()`）。

## 结构

- `contracts/L1FL.sol` — L1 主链账本：登记参与方、存储 L2 上报的聚合结果、激励占位
- `contracts/L2FL.sol` — L2 聚合层：客户端申请/上传、服务端下发参数、聚合后上报 L1
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

1. 客户端申请 `L2FL.applyToJoin()`
2. 服务端给参数 `L2FL.distributeParameters()`
3. 客户端本地训练（off-chain）
4. 客户端上传到 L2 `L2FL.uploadParameters()`
5. L2 分析后上传 L1 `L2FL.analyzeAndAggregate()` → `commitToL1()` → `IL1FL.commitRound()`

## 约定

- 框架阶段只填签名与 TODO 注释，不写业务实现。
- 函数体以 `revert NotImplemented()` 占位，避免空实现被误调用。
- 本目录合约由 off-chain `src/python` Flower 客户端/服务端配合驱动。
