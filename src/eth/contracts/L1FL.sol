// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IL1FL} from "../interfaces/IL1FL.sol";

/// @title L1FL — L1 主链联邦学习账本
/// @notice 联邦学习的最终权威层：登记参与方，接收并存储 L2 上报的聚合结果，
///         记录激励/声誉。
/// @dev    ⚠️ 框架文件：仅定义结构与函数签名，函数体均为 `revert NotImplemented()`，
///         具体实现待后续填充（见各函数 TODO 注释）。
contract L1FL is IL1FL {
    // ---------- 数据结构 ----------

    enum Role { NONE, CLIENT, SERVER, L2 }

    /// 参与方（客户端 / 服务端 / L2 聚合器）的登记记录。
    struct Participant {
        address addr;
        Role role;
        uint256 registeredAt;
        bool active;
    }

    // ---------- 状态变量 ----------

    address public owner;
    mapping(address => Participant) public participants; // 地址 => 参与方
    mapping(uint256 => RoundRecord) public rounds;        // 轮次 => 聚合记录
    uint256 public latestRound;                           // 最近已落账轮次

    // ---------- 事件 ----------

    event ParticipantRegistered(address indexed addr, Role role);
    event RoundCommitted(uint256 indexed round, bytes32 aggregatedHash, uint256 participantCount);
    event RewardPaid(address indexed participant, uint256 amount);

    // ---------- 错误 ----------

    error NotImplemented(); // 框架占位：函数尚未实现
    error NotOwner();
    error OnlyRegisteredL2(address caller);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    // ---------- 函数（框架占位） ----------

    /// 登记参与方（客户端 / 服务端 / L2）。
    /// @param addr 参与方地址
    /// @param role 角色
    /// TODO：鉴权、防重复登记、参与方数量上限与准入策略。
    
    function registerParticipant(address addr, Role role) external {
        revert NotImplemented();
    }

    /// 接收 L2 上报的某轮聚合结果并落账。
    /// TODO：仅允许已登记的 L2 调用（modifier OnlyRegisteredL2）；轮次单调递增校验；
    ///       建议记录 aggregatedHash 的提交者，便于审计与后续激励结算。
    function commitRound(
        uint256 round,
        bytes32 aggregatedHash,
        uint256 participantCount,
        string calldata metadataUri
    ) external override {
        revert NotImplemented();
    }

    /// 查询某轮在 L1 上的最终聚合记录。
    /// @return RoundRecord 见 IL1FL.RoundRecord
    function getRound(uint256 round) external view override returns (RoundRecord memory) {
        return rounds[round];
    }

    /// 向参与方发放激励。
    /// @param participant 收款参与方
    /// @param amount      发放数量（wei）
    /// TODO：关联到具体轮次与参与质量（如上传是否被采纳），并支持从资金池按结果结算。
    function payReward(address participant, uint256 amount) external onlyOwner {
        revert NotImplemented();
    }
}
