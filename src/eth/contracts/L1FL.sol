// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IL1FL} from "../interfaces/IL1FL.sol";

/// @title L1FL — L1 主链联邦学习账本
/// @notice 联邦学习的最终权威层：登记参与方，接收 L2 上报的聚合结果并经"提交 → 挑战 → 确定"
///         的乐观流程落账，记录激励/声誉。
///
/// 轮次生命周期（乐观落账，押金驱动）：
///   NONE ──commitRound(押 commitBond)──▶ PENDING ──窗口过后 finalizeRound──▶ FINALIZED
///                                          │  ▲
///                      challenge(押 challengeBond)│  │ resolveChallenge(驳回挑战)：挑战押金 → 提交方
///                                          ▼  │
///                                      CHALLENGED ──resolveChallenge(挑战成立)──▶ REJECTED
///                                                    （提交押金 + 挑战押金 → 挑战者）
///
///   - 仅已登记的 L2 角色可提交；任何人可押金挑战；finalize 无权限、仅受时间约束。
///   - 押金/奖励一律记入 pendingWithdrawals，由收款方自行 withdraw()（pull 模式，避免转账失败卡住流程）。
///   - resolveChallenge 目前由 owner 充当仲裁人：这是明确的信任占位，后续由链上欺诈证明
///     （交互式二分 / ZK 验证器）替换，此处即插入点。
///
/// @dev  payReward 仍为 `revert NotImplemented()` 占位。
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
    uint256 public immutable challengePeriod; // 挑战窗口长度（秒）
    uint256 public immutable commitBond;      // 提交押金（wei）
    uint256 public immutable challengeBond;   // 挑战押金（wei）

    mapping(address => Participant) public participants; // 地址 => 参与方
    mapping(uint256 => RoundRecord) public rounds;        // 轮次 => 落账记录
    mapping(address => uint256) public pendingWithdrawals; // 待提取余额（押金退还 / 奖励）
    uint256 public latestRound;                           // 最近已 FINALIZED 的最大轮次

    // ---------- 事件 ----------

    event ParticipantRegistered(address indexed addr, Role role);
    event RoundCommitted(
        uint256 indexed round, address indexed committer, bytes32 aggregatedHash,
        uint256 participantCount, uint256 finalizeAfter
    );
    event RoundChallenged(uint256 indexed round, address indexed challenger);
    event ChallengeResolved(uint256 indexed round, address indexed challenger, bool upheld);
    event RoundFinalized(uint256 indexed round, bytes32 aggregatedHash);
    event Withdrawn(address indexed to, uint256 amount);
    event RewardPaid(address indexed participant, uint256 amount);

    // ---------- 错误 ----------

    error NotImplemented(); // 框架占位：函数尚未实现
    error NotOwner();
    error OnlyRegisteredL2(address caller);
    error InvalidRole();           // role == NONE
    error AlreadyRegistered();     // 地址已登记
    error InvalidRound();          // round == 0
    error InvalidHash();           // aggregatedHash == bytes32(0)
    error RoundExists();           // 该轮已提交过（任何非 NONE 状态）
    error WrongBond(uint256 expected, uint256 actual);
    error RoundNotPending();       // 期望 PENDING
    error RoundNotChallenged();    // 期望 CHALLENGED
    error ChallengeWindowClosed(); // 挑战窗口已过
    error ChallengeWindowOpen();   // 挑战窗口未过，尚不可 finalize
    error NothingToWithdraw();
    error TransferFailed();

    constructor(uint256 challengePeriod_, uint256 commitBond_, uint256 challengeBond_) {
        owner = msg.sender;
        challengePeriod = challengePeriod_;
        commitBond = commitBond_;
        challengeBond = challengeBond_;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyRegisteredL2() {
        Participant storage p = participants[msg.sender];
        if (p.role != Role.L2 || !p.active) revert OnlyRegisteredL2(msg.sender);
        _;
    }

    // ---------- 参与方登记 ----------

    /// 登记参与方（客户端 / 服务端 / L2）。
    /// @param addr 参与方地址
    /// @param role 角色
    /// @notice 框架阶段由 owner 登记；准入策略 / 数量上限 / 质押后续扩展。
    function registerParticipant(address addr, Role role) external onlyOwner {
        if (role == Role.NONE) revert InvalidRole();
        if (participants[addr].role != Role.NONE) revert AlreadyRegistered();
        participants[addr] = Participant(addr, role, block.timestamp, true);
        emit ParticipantRegistered(addr, role);
    }

    // ---------- 轮次生命周期：提交 → 挑战 → 确定 ----------

    /// [1] L2 提交某轮聚合结果，附 commitBond 押金，进入挑战窗口。
    function commitRound(
        uint256 round,
        bytes32 aggregatedHash,
        uint256 participantCount,
        string calldata metadataUri
    ) external payable override onlyRegisteredL2 {
        if (round == 0) revert InvalidRound();
        if (aggregatedHash == bytes32(0)) revert InvalidHash();
        if (rounds[round].status != RoundStatus.NONE) revert RoundExists();
        if (msg.value != commitBond) revert WrongBond(commitBond, msg.value);

        uint256 finalizeAfter = block.timestamp + challengePeriod; // 时间由共识赋值
        rounds[round] = RoundRecord({
            round: round,
            aggregatedHash: aggregatedHash,
            participantCount: participantCount,
            metadataUri: metadataUri,
            committedAt: block.timestamp,
            committer: msg.sender,
            finalizeAfter: finalizeAfter,
            status: RoundStatus.PENDING,
            challenger: address(0)
        });
        emit RoundCommitted(round, msg.sender, aggregatedHash, participantCount, finalizeAfter);
    }

    /// [2] 窗口内任何人押 challengeBond 挑战某轮提交；进入 CHALLENGED，阻断 finalize 直至仲裁。
    function challenge(uint256 round) external payable {
        RoundRecord storage rec = rounds[round];
        if (rec.status != RoundStatus.PENDING) revert RoundNotPending();
        if (block.timestamp >= rec.finalizeAfter) revert ChallengeWindowClosed();
        if (msg.value != challengeBond) revert WrongBond(challengeBond, msg.value);

        rec.status = RoundStatus.CHALLENGED;
        rec.challenger = msg.sender;
        emit RoundChallenged(round, msg.sender);
    }

    /// [2'] 仲裁挑战。upheld=true：挑战成立，轮次 REJECTED，两份押金判给挑战者；
    ///      upheld=false：挑战驳回，挑战押金判给提交方，轮次回到 PENDING（窗口不延长，
    ///      若窗口已过则可立即 finalize）。
    /// @dev 信任占位：由 owner 仲裁。后续替换为链上欺诈证明验证（交互式二分 / ZK verifier）。
    function resolveChallenge(uint256 round, bool upheld) external onlyOwner {
        RoundRecord storage rec = rounds[round];
        if (rec.status != RoundStatus.CHALLENGED) revert RoundNotChallenged();

        address challenger = rec.challenger;
        rec.challenger = address(0);
        if (upheld) {
            rec.status = RoundStatus.REJECTED;
            pendingWithdrawals[challenger] += challengeBond + commitBond; // 提交方被罚没
        } else {
            rec.status = RoundStatus.PENDING;
            pendingWithdrawals[rec.committer] += challengeBond; // 挑战者被罚没
        }
        emit ChallengeResolved(round, challenger, upheld);
    }

    /// [3] 挑战窗口过后且无未决挑战，任何人可确定该轮；提交押金退还提交方。
    function finalizeRound(uint256 round) external {
        RoundRecord storage rec = rounds[round];
        if (rec.status != RoundStatus.PENDING) revert RoundNotPending();
        if (block.timestamp < rec.finalizeAfter) revert ChallengeWindowOpen();

        rec.status = RoundStatus.FINALIZED;
        pendingWithdrawals[rec.committer] += commitBond;
        if (round > latestRound) latestRound = round;
        emit RoundFinalized(round, rec.aggregatedHash);
    }

    /// 提取本地址累计的押金退还 / 奖励（pull 模式）。
    function withdraw() external {
        uint256 amount = pendingWithdrawals[msg.sender];
        if (amount == 0) revert NothingToWithdraw();
        pendingWithdrawals[msg.sender] = 0; // 先清零再转账，防重入
        (bool ok, ) = msg.sender.call{value: amount}("");
        if (!ok) revert TransferFailed();
        emit Withdrawn(msg.sender, amount);
    }

    // ---------- 查询 ----------

    /// 查询某轮在 L1 上的落账记录（含当前状态）。
    function getRound(uint256 round) external view override returns (RoundRecord memory) {
        return rounds[round];
    }

    // ---------- 激励（占位） ----------

    /// 向参与方发放激励。
    /// @param participant 收款参与方
    /// @param amount      发放数量（wei）
    /// TODO：关联到具体已 FINALIZED 轮次与参与质量（如上传是否被采纳），从资金池按结果结算。
    function payReward(address participant, uint256 amount) external onlyOwner {
        revert NotImplemented();
    }
}
