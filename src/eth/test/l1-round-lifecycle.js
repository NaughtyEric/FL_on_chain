// L1 轮次生命周期：提交（押金）→ 挑战（押金）→ 仲裁 → 确定，以及押金结算的 pull 提取。
const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

const CHALLENGE_PERIOD = 7 * 24 * 3600; // 7 天
const COMMIT_BOND = ethers.parseEther("1");
const CHALLENGE_BOND = ethers.parseEther("0.5");

// RoundStatus / Role 枚举值（与 IL1FL / L1FL 中声明顺序一致）
const Status = { NONE: 0, PENDING: 1, CHALLENGED: 2, FINALIZED: 3, REJECTED: 4 };
const Role = { NONE: 0, CLIENT: 1, SERVER: 2, L2: 3 };

const HASH = ethers.keccak256(ethers.toUtf8Bytes("aggregated-round-1"));
const URI = "http://127.0.0.1:9000/files/deadbeef";

describe("L1FL round lifecycle (commit -> challenge -> finalize)", function () {
  let l1, owner, l2, challenger, stranger;

  beforeEach(async function () {
    [owner, l2, challenger, stranger] = await ethers.getSigners();
    const L1FL = await ethers.getContractFactory("L1FL");
    l1 = await L1FL.deploy(CHALLENGE_PERIOD, COMMIT_BOND, CHALLENGE_BOND);
    await l1.waitForDeployment();
    await l1.registerParticipant(l2.address, Role.L2);
  });

  const commit = (round = 1) =>
    l1.connect(l2).commitRound(round, HASH, 2, URI, { value: COMMIT_BOND });

  describe("registerParticipant", function () {
    it("records the participant and rejects duplicates / NONE role / non-owner", async function () {
      const p = await l1.participants(l2.address);
      expect(p.role).to.equal(Role.L2);
      expect(p.active).to.equal(true);

      await expect(l1.registerParticipant(l2.address, Role.L2))
        .to.be.revertedWithCustomError(l1, "AlreadyRegistered");
      await expect(l1.registerParticipant(stranger.address, Role.NONE))
        .to.be.revertedWithCustomError(l1, "InvalidRole");
      await expect(l1.connect(stranger).registerParticipant(stranger.address, Role.CLIENT))
        .to.be.revertedWithCustomError(l1, "NotOwner");
    });
  });

  describe("commitRound", function () {
    it("only a registered L2 may commit", async function () {
      await expect(l1.connect(stranger).commitRound(1, HASH, 2, URI, { value: COMMIT_BOND }))
        .to.be.revertedWithCustomError(l1, "OnlyRegisteredL2").withArgs(stranger.address);
      // 登记为 CLIENT 也不行
      await l1.registerParticipant(stranger.address, Role.CLIENT);
      await expect(l1.connect(stranger).commitRound(1, HASH, 2, URI, { value: COMMIT_BOND }))
        .to.be.revertedWithCustomError(l1, "OnlyRegisteredL2");
    });

    it("validates round / hash / bond and rejects duplicate rounds", async function () {
      await expect(l1.connect(l2).commitRound(0, HASH, 2, URI, { value: COMMIT_BOND }))
        .to.be.revertedWithCustomError(l1, "InvalidRound");
      await expect(l1.connect(l2).commitRound(1, ethers.ZeroHash, 2, URI, { value: COMMIT_BOND }))
        .to.be.revertedWithCustomError(l1, "InvalidHash");
      await expect(l1.connect(l2).commitRound(1, HASH, 2, URI, { value: 0 }))
        .to.be.revertedWithCustomError(l1, "WrongBond").withArgs(COMMIT_BOND, 0);
      await commit();
      await expect(commit()).to.be.revertedWithCustomError(l1, "RoundExists");
    });

    it("opens a PENDING round with a consensus-timestamped challenge window", async function () {
      const tx = await commit();
      const receipt = await tx.wait();
      const blockTime = (await ethers.provider.getBlock(receipt.blockNumber)).timestamp;
      const finalizeAfter = blockTime + CHALLENGE_PERIOD;

      await expect(tx).to.emit(l1, "RoundCommitted").withArgs(1, l2.address, HASH, 2, finalizeAfter);
      const rec = await l1.getRound(1);
      expect(rec.status).to.equal(Status.PENDING);
      expect(rec.committer).to.equal(l2.address);
      expect(rec.aggregatedHash).to.equal(HASH);
      expect(rec.participantCount).to.equal(2);
      expect(rec.metadataUri).to.equal(URI);
      expect(rec.committedAt).to.equal(blockTime);
      expect(rec.finalizeAfter).to.equal(finalizeAfter);
      expect(rec.challenger).to.equal(ethers.ZeroAddress);
      expect(await ethers.provider.getBalance(await l1.getAddress())).to.equal(COMMIT_BOND);
    });
  });

  describe("finalizeRound (happy path, no challenge)", function () {
    it("is blocked while the window is open, then anyone can finalize", async function () {
      await commit();
      await expect(l1.finalizeRound(1)).to.be.revertedWithCustomError(l1, "ChallengeWindowOpen");

      await time.increase(CHALLENGE_PERIOD);
      await expect(l1.connect(stranger).finalizeRound(1)).to.emit(l1, "RoundFinalized").withArgs(1, HASH);

      expect((await l1.getRound(1)).status).to.equal(Status.FINALIZED);
      expect(await l1.latestRound()).to.equal(1);
      // 提交押金退回提交方的待提取余额
      expect(await l1.pendingWithdrawals(l2.address)).to.equal(COMMIT_BOND);

      // 已确定的轮次不可再 finalize / challenge
      await expect(l1.finalizeRound(1)).to.be.revertedWithCustomError(l1, "RoundNotPending");
      await expect(l1.connect(challenger).challenge(1, { value: CHALLENGE_BOND }))
        .to.be.revertedWithCustomError(l1, "RoundNotPending");
    });

    it("latestRound tracks the highest finalized round, not commit order", async function () {
      await commit(5);
      await commit(3);
      await time.increase(CHALLENGE_PERIOD);
      await l1.finalizeRound(5);
      expect(await l1.latestRound()).to.equal(5);
      await l1.finalizeRound(3);
      expect(await l1.latestRound()).to.equal(5);
    });

    it("rejects unknown rounds", async function () {
      await expect(l1.finalizeRound(42)).to.be.revertedWithCustomError(l1, "RoundNotPending");
      await expect(l1.challenge(42, { value: CHALLENGE_BOND }))
        .to.be.revertedWithCustomError(l1, "RoundNotPending");
    });
  });

  describe("challenge", function () {
    it("requires the exact bond and an open window", async function () {
      await commit();
      await expect(l1.connect(challenger).challenge(1, { value: 0 }))
        .to.be.revertedWithCustomError(l1, "WrongBond").withArgs(CHALLENGE_BOND, 0);

      await time.increase(CHALLENGE_PERIOD);
      await expect(l1.connect(challenger).challenge(1, { value: CHALLENGE_BOND }))
        .to.be.revertedWithCustomError(l1, "ChallengeWindowClosed");
    });

    it("moves the round to CHALLENGED and blocks finalize until resolved", async function () {
      await commit();
      await expect(l1.connect(challenger).challenge(1, { value: CHALLENGE_BOND }))
        .to.emit(l1, "RoundChallenged").withArgs(1, challenger.address);

      const rec = await l1.getRound(1);
      expect(rec.status).to.equal(Status.CHALLENGED);
      expect(rec.challenger).to.equal(challenger.address);

      // 同轮不可重复挑战；窗口过后也不能 finalize（必须先仲裁）
      await expect(l1.connect(stranger).challenge(1, { value: CHALLENGE_BOND }))
        .to.be.revertedWithCustomError(l1, "RoundNotPending");
      await time.increase(CHALLENGE_PERIOD);
      await expect(l1.finalizeRound(1)).to.be.revertedWithCustomError(l1, "RoundNotPending");
    });
  });

  describe("resolveChallenge", function () {
    beforeEach(async function () {
      await commit();
      await l1.connect(challenger).challenge(1, { value: CHALLENGE_BOND });
    });

    it("is owner-only and requires a CHALLENGED round", async function () {
      await expect(l1.connect(stranger).resolveChallenge(1, true))
        .to.be.revertedWithCustomError(l1, "NotOwner");
      await expect(l1.resolveChallenge(2, true))
        .to.be.revertedWithCustomError(l1, "RoundNotChallenged");
    });

    it("upheld: rejects the round and awards both bonds to the challenger", async function () {
      await expect(l1.resolveChallenge(1, true))
        .to.emit(l1, "ChallengeResolved").withArgs(1, challenger.address, true);

      const rec = await l1.getRound(1);
      expect(rec.status).to.equal(Status.REJECTED);
      expect(rec.challenger).to.equal(ethers.ZeroAddress);
      expect(await l1.pendingWithdrawals(challenger.address)).to.equal(COMMIT_BOND + CHALLENGE_BOND);
      expect(await l1.pendingWithdrawals(l2.address)).to.equal(0);
      expect(await l1.latestRound()).to.equal(0);

      // 被驳回的轮次是终态：不能 finalize、不能重新提交同一轮号
      await time.increase(CHALLENGE_PERIOD);
      await expect(l1.finalizeRound(1)).to.be.revertedWithCustomError(l1, "RoundNotPending");
      await expect(commit()).to.be.revertedWithCustomError(l1, "RoundExists");
    });

    it("dismissed: returns to PENDING, awards challenge bond to committer, window unchanged", async function () {
      const before = await l1.getRound(1);
      await expect(l1.resolveChallenge(1, false))
        .to.emit(l1, "ChallengeResolved").withArgs(1, challenger.address, false);

      const rec = await l1.getRound(1);
      expect(rec.status).to.equal(Status.PENDING);
      expect(rec.challenger).to.equal(ethers.ZeroAddress);
      expect(rec.finalizeAfter).to.equal(before.finalizeAfter); // 窗口不延长
      expect(await l1.pendingWithdrawals(l2.address)).to.equal(CHALLENGE_BOND);
      expect(await l1.pendingWithdrawals(challenger.address)).to.equal(0);

      // 窗口仍开着：可以再次被挑战（每次都要押金）
      await l1.connect(stranger).challenge(1, { value: CHALLENGE_BOND });
      expect((await l1.getRound(1)).challenger).to.equal(stranger.address);
      await l1.resolveChallenge(1, false);

      // 窗口过后 finalize：提交方累计拿回自己的押金 + 两笔挑战押金
      await time.increase(CHALLENGE_PERIOD);
      await l1.finalizeRound(1);
      expect((await l1.getRound(1)).status).to.equal(Status.FINALIZED);
      expect(await l1.pendingWithdrawals(l2.address)).to.equal(COMMIT_BOND + CHALLENGE_BOND * 2n);
    });

    it("dismissed after the window has already passed: finalize is immediately available", async function () {
      await time.increase(CHALLENGE_PERIOD);
      await l1.resolveChallenge(1, false);
      await l1.finalizeRound(1);
      expect((await l1.getRound(1)).status).to.equal(Status.FINALIZED);
    });
  });

  describe("withdraw", function () {
    it("pays out the pending balance exactly once", async function () {
      await commit();
      await l1.connect(challenger).challenge(1, { value: CHALLENGE_BOND });
      await l1.resolveChallenge(1, true);

      const owed = COMMIT_BOND + CHALLENGE_BOND;
      const tx = l1.connect(challenger).withdraw();
      await expect(tx).to.changeEtherBalances([challenger, l1], [owed, -owed]);
      await expect(tx).to.emit(l1, "Withdrawn").withArgs(challenger.address, owed);

      expect(await l1.pendingWithdrawals(challenger.address)).to.equal(0);
      await expect(l1.connect(challenger).withdraw()).to.be.revertedWithCustomError(l1, "NothingToWithdraw");
      expect(await ethers.provider.getBalance(await l1.getAddress())).to.equal(0);
    });

    it("reverts when nothing is owed", async function () {
      await expect(l1.connect(stranger).withdraw()).to.be.revertedWithCustomError(l1, "NothingToWithdraw");
    });
  });
});
