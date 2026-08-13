// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title IL1FL — L1 主链联邦学习账本的跨链接口
/// @notice L2 聚合分析完成后，经跨链桥以本接口把最终结果上报 L1。
///         仅定义 L1 对 L2 暴露的调用面，结构体与 L1FL 合约共享。
interface IL1FL {
    /// 单轮聚合结果在 L1 上的落账记录。
    struct RoundRecord {
        uint256 round;            // 联邦学习轮次号
        bytes32 aggregatedHash;   // 聚合后模型/参数的哈希（如 SHA-256）
        uint256 participantCount; // 参与该轮的客户端数量
        string metadataUri;       // 指向链下聚合数据的 URI（如 IPFS）
        uint256 committedAt;      // 落账时间戳
    }

    /// 上报一个已完成轮次的聚合结果（由 L2 经桥调用）。
    /// @param round           轮次号
    /// @param aggregatedHash  聚合后参数哈希
    /// @param participantCount 参与客户端数量
    /// @param metadataUri     链下聚合数据 URI
    function commitRound(
        uint256 round,
        bytes32 aggregatedHash,
        uint256 participantCount,
        string calldata metadataUri
    ) external;

    /// 查询某轮在 L1 上的最终聚合记录。
    function getRound(uint256 round) external view returns (RoundRecord memory);
}
