// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title IL1FL — L1 主链联邦学习账本的跨链接口
/// @notice L2 聚合分析完成后，经跨链桥以本接口把最终结果上报 L1。
///         仅定义 L1 对 L2 暴露的调用面，结构体与 L1FL 合约共享。
///
/// 乐观落账：commitRound 只是"提交"，进入挑战窗口（PENDING）；窗口内任何人可押金挑战，
/// 窗口过后无有效挑战即可 finalize。见 L1FL 中 challenge / resolveChallenge / finalizeRound。
interface IL1FL {
    /// 单轮在 L1 上的生命周期状态。
    enum RoundStatus { NONE, PENDING, CHALLENGED, FINALIZED, REJECTED }

    /// 单轮聚合结果在 L1 上的落账记录。
    struct RoundRecord {
        uint256 round;            // 联邦学习轮次号
        bytes32 aggregatedHash;   // 聚合后模型/参数的哈希（如 SHA-256）
        uint256 participantCount; // 参与该轮的客户端数量
        string metadataUri;       // 指向链下聚合数据的 URI（如 IPFS / scripts/storage）
        uint256 committedAt;      // 提交时间戳（block.timestamp，共识赋值）
        address committer;        // 提交方（已登记的 L2）
        uint256 finalizeAfter;    // 挑战窗口截止时间：>= 此时刻方可 finalize
        RoundStatus status;       // 生命周期状态
        address challenger;       // 当前挑战者（仅 CHALLENGED 状态有效）
    }

    /// 提交一个已完成轮次的聚合结果（由 L2 经桥调用），进入挑战窗口。
    /// @dev 需随调用附带 commitBond 数量的 ETH 作为押金；轮次被驳回时押金判给挑战者。
    /// @param round           轮次号
    /// @param aggregatedHash  聚合后参数哈希
    /// @param participantCount 参与客户端数量
    /// @param metadataUri     链下聚合数据 URI
    function commitRound(
        uint256 round,
        bytes32 aggregatedHash,
        uint256 participantCount,
        string calldata metadataUri
    ) external payable;

    /// 查询某轮在 L1 上的落账记录（含当前状态）。
    function getRound(uint256 round) external view returns (RoundRecord memory);
}
