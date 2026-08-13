// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IL1FL} from "../interfaces/IL1FL.sol";

/// @title L2FL — L2 聚合/暂存层
/// @notice 联邦学习的主要业务发生地：客户端在本层申请加入、接收服务端下发的参数、
///         本地训练完成后上传更新；L2 校验并聚合分析，最后经跨链桥把结果上报 L1。
///
/// 整体流程（与 off-chain Flower 客户端/服务端配合）：
///   1. 客户端申请        -> applyToJoin()
///   2. 服务端下发参数     -> distributeParameters()（off-chain 下发，链上仅记哈希）
///   3. 客户端本地训练     -> off-chain（PyTorch 在 src/python/fl_client 完成）
///   4. 客户端上传到 L2    -> uploadParameters()
///   5. L2 分析并上传 L1   -> analyzeAndAggregate() + commitToL1() -> IL1FL.commitRound()
///
/// @dev  ⚠️ 框架文件：仅定义结构与函数签名，函数体均为 `revert NotImplemented()`，
///       具体实现待后续填充（见各函数 TODO 注释）。
contract L2FL {
    // ---------- 数据结构 ----------

    enum ClientStatus { NONE, APPLIED, APPROVED, UPLOADED, COMMITTED }

    /// 单个客户端在某轮的参与记录。
    struct ClientRecord {
        address client;
        uint256 round;
        ClientStatus status;    // 生命周期：申请 -> 通过 -> 上传 -> 已聚合
        bytes32 paramHash;      // 本地训练后上传的参数哈希
        bytes32 proofHash;      // 训练证明/零知识证明哈希（占位，后续扩展）
        uint256 uploadedAt;
    }

    /// 单个联邦学习轮次的聚合信息。
    struct RoundInfo {
        uint256 numClients;     // 本轮应参与客户端数
        uint256 uploadCount;    // 已上传客户端数
        bytes32 aggregatedHash; // 聚合后参数哈希
        uint256 closeAt;        // 上传截止时间（占位，后续扩展为 deadline）
        bool committedToL1;     // 是否已上报 L1
    }

    // ---------- 状态变量 ----------

    address public owner;
    address public l1; // L1 账本地址（跨链桥对端，构造时指定）
    mapping(address => ClientRecord) public clients; // 客户端 => 参与记录
    mapping(uint256 => RoundInfo) public rounds;      // 轮次 => 聚合信息
    uint256 public latestRound;

    // ---------- 事件 ----------

    event ClientApplied(address indexed client);
    event ParamsDistributed(uint256 indexed round, bytes32 paramsHash);
    event ClientUploaded(address indexed client, uint256 indexed round, bytes32 paramHash);
    event RoundCommittedToL1(uint256 indexed round, bytes32 aggregatedHash);

    // ---------- 错误 ----------

    error NotImplemented(); // 框架占位：函数尚未实现
    error NotOwner();

    constructor(address l1_) {
        owner = msg.sender;
        l1 = l1_; // L1 账本地址（跨链桥对端）
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    // ---------- 函数（框架占位） ----------

    /// [流程 1] 客户端申请加入联邦学习。
    /// TODO：身份校验、登记为 APPLIED、分配/创建轮次、触发申请事件。
    function applyToJoin() external {
        revert NotImplemented();
    }

    /// [流程 2] 服务端下发本轮全局参数（链上仅记录参数哈希，实际参数 off-chain 下发）。
    /// @param round      轮次号
    /// @param paramsHash 全局参数哈希（如 SHA-256）
    /// TODO：仅允许服务端角色调用；校验轮次未关闭；记录 ParamsDistributed。
    function distributeParameters(uint256 round, bytes32 paramsHash) external onlyOwner {
        revert NotImplemented();
    }

    /// [流程 4] 客户端上传本地训练后的参数到 L2。
    /// @param round      轮次号
    /// @param paramHash  本地训练后参数哈希
    /// @param proofHash  训练证明/零知识证明哈希（占位）
    /// TODO：校验申请已通过、轮次未截止；置 UPLOADED 并累加 uploadCount；
    ///       建议同一客户端单轮仅可上传一次（防重复）。
    function uploadParameters(uint256 round, bytes32 paramHash, bytes32 proofHash) external {
        revert NotImplemented();
    }

    /// [流程 5a] L2 分析本轮：校验证明、聚合上传的参数并计算 aggregatedHash。
    /// @param round 轮次号
    /// TODO：达到最小参与数后聚合；校验证明有效性；记录 aggregatedHash。
    function analyzeAndAggregate(uint256 round) external onlyOwner {
        revert NotImplemented();
    }

    /// [流程 5b] 把聚合结果经跨链桥上报 L1（调用 IL1FL.commitRound）。
    /// @param round 轮次号
    /// TODO：确认分析完成、尚未上报；通过桥（此处为直调 l1 地址占位）上报；
    ///       置 committedToL1 = true 并触发 RoundCommittedToL1。
    function commitToL1(uint256 round) external onlyOwner {
        revert NotImplemented();
    }

    /// 查询客户端参与记录。
    function getClient(address client) external view returns (ClientRecord memory) {
        return clients[client];
    }
}
