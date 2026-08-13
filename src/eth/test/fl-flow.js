// 框架冒烟测试：验证部署接线、访问控制、占位函数行为与初始视图状态。
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("FL on-chain flow (framework)", function () {
  let l1, l2, owner, client;

  beforeEach(async function () {
    [owner, client] = await ethers.getSigners();

    const L1FL = await ethers.getContractFactory("L1FL");
    l1 = await L1FL.deploy();
    await l1.waitForDeployment();

    const L2FL = await ethers.getContractFactory("L2FL");
    l2 = await L2FL.deploy(await l1.getAddress());
    await l2.waitForDeployment();
  });

  it("wires L2 to L1", async function () {
    expect(await l2.l1()).to.equal(await l1.getAddress());
  });

  it("restricts owner-only functions", async function () {
    const hash = ethers.keccak256(ethers.toUtf8Bytes("params"));
    await expect(l2.connect(client).distributeParameters(1, hash)).to.be.revertedWithCustomError(l2, "NotOwner");
    await expect(l2.connect(client).analyzeAndAggregate(1)).to.be.revertedWithCustomError(l2, "NotOwner");
    await expect(l2.connect(client).commitToL1(1)).to.be.revertedWithCustomError(l2, "NotOwner");
    await expect(l1.connect(client).payReward(client.address, 1)).to.be.revertedWithCustomError(l1, "NotOwner");
  });

  it("stub functions revert with NotImplemented", async function () {
    const hash = ethers.keccak256(ethers.toUtf8Bytes("params"));

    // 流程 1：客户端申请
    await expect(l2.connect(client).applyToJoin()).to.be.revertedWithCustomError(l2, "NotImplemented");
    // 流程 2：服务端下发参数
    await expect(l2.distributeParameters(1, hash)).to.be.revertedWithCustomError(l2, "NotImplemented");
    // 流程 4：客户端上传到 L2
    await expect(l2.connect(client).uploadParameters(1, hash, hash)).to.be.revertedWithCustomError(l2, "NotImplemented");
    // 流程 5：L2 分析 + 上报 L1
    await expect(l2.analyzeAndAggregate(1)).to.be.revertedWithCustomError(l2, "NotImplemented");
    await expect(l2.commitToL1(1)).to.be.revertedWithCustomError(l2, "NotImplemented");
    // L1 登记/落账
    await expect(l1.registerParticipant(client.address, 1)).to.be.revertedWithCustomError(l1, "NotImplemented");
  });

  it("view getters return initial state", async function () {
    const rec = await l2.getClient(client.address);
    expect(rec.round).to.equal(0);

    const round = await l1.getRound(1);
    expect(round.round).to.equal(0);

    expect(await l1.latestRound()).to.equal(0);
    expect(await l1.owner()).to.equal(owner.address);
    expect(await l2.owner()).to.equal(owner.address);
  });
});
