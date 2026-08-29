# eth

FL 链上账本合约。已实现：参与方申请（`applyToJoin`，申请即自动 APPROVED）、上传参数 id（`uploadParameters`）、按 id 查询（`getByParamId`）。其余（`distributeParameters`/`analyzeAndAggregate`/`commitToL1` 及 L1FL 全部）仍为 `revert NotImplemented()` 占位。

- `contracts/L1FL.sol` L1 账本 · `contracts/L2FL.sol` L2 聚合层 · `interfaces/IL1FL.sol` 跨链接口 · `test/fl-flow.js` · `scripts/deploy.js`

```text
npx hardhat compile | test | node          # node: 127.0.0.1:8545, chainId 31337
npx hardhat run scripts/deploy.js --network localhost
```

## 约定

- 参数 id 来自链下 `scripts/storage/` 的 sha256（对应 DCMF-BFL 论文的 CID）；大对象永不上链。
- `uploadedAt` 由 `block.timestamp` 共识赋值（不接受调用方传入），随 `ClientUploaded` 事件落日志，作为不可篡改时间凭证。
- 未实现函数保持 `revert NotImplemented()` 占位，不写空实现。
- 合约由 off-chain `src/python` Flower 客户端/服务端驱动（集成未实现）。
