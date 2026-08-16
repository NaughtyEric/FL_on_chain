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

    // 流程 2：服务端下发参数
    await expect(l2.distributeParameters(1, hash)).to.be.revertedWithCustomError(l2, "NotImplemented");
    // 流程 5：L2 分析 + 上报 L1
    await expect(l2.analyzeAndAggregate(1)).to.be.revertedWithCustomError(l2, "NotImplemented");
    await expect(l2.commitToL1(1)).to.be.revertedWithCustomError(l2, "NotImplemented");
    // L1 登记/落账
    await expect(l1.registerParticipant(client.address, 1)).to.be.revertedWithCustomError(l1, "NotImplemented");
  });

  it("applies to join: client becomes APPROVED; duplicate apply reverts", async function () {
    await l2.connect(client).applyToJoin();
    let rec = await l2.getClient(client.address);
    expect(rec.client).to.equal(client.address);
    expect(rec.status).to.equal(2); // APPROVED

    await expect(l2.connect(client).applyToJoin()).to.be.revertedWithCustomError(l2, "AlreadyApplied");
  });

  it("uploads a parameter id and records it in the content-addressed table", async function () {
    await l2.connect(client).applyToJoin();
    const paramId = ethers.keccak256(ethers.toUtf8Bytes("client-update-1"));
    const proofHash = ethers.keccak256(ethers.toUtf8Bytes("training-proof"));

    await expect(l2.connect(client).uploadParameters(1, paramId, proofHash))
      .to.emit(l2, "ClientUploaded")
      .withArgs(client.address, 1, paramId);

    // 按参数 id 查询登记记录
    const rec = await l2.getByParamId(paramId);
    expect(rec.client).to.equal(client.address);
    expect(rec.round).to.equal(1);
    expect(rec.proofHash).to.equal(proofHash);
    expect(rec.uploadedAt).to.be.gt(0);

    // 客户端记录同步更新
    const crec = await l2.getClient(client.address);
    expect(crec.status).to.equal(3); // UPLOADED
    expect(crec.round).to.equal(1);
    expect(crec.paramHash).to.equal(paramId);
    expect(crec.proofHash).to.equal(proofHash);

    // 同客户端下一轮可再次上传（同轮仅一次，跨轮放行）
    const paramId2 = ethers.keccak256(ethers.toUtf8Bytes("client-update-2"));
    await l2.connect(client).uploadParameters(2, paramId2, proofHash);
    const rec2 = await l2.getByParamId(paramId2);
    expect(rec2.client).to.equal(client.address);
    expect(rec2.round).to.equal(2);
  });

  it("returns a zero record for unknown parameter id", async function () {
    const rec = await l2.getByParamId(ethers.keccak256(ethers.toUtf8Bytes("unknown")));
    expect(rec.client).to.equal(ethers.ZeroAddress);
    expect(rec.round).to.equal(0);
    expect(rec.proofHash).to.equal(ethers.ZeroHash);
    expect(rec.uploadedAt).to.equal(0);
  });

  it("rejects invalid uploads", async function () {
    const paramId = ethers.keccak256(ethers.toUtf8Bytes("params"));
    const zero = ethers.ZeroHash;

    // 未申请直接上传 -> NotApproved
    await expect(l2.connect(client).uploadParameters(1, paramId, zero))
      .to.be.revertedWithCustomError(l2, "NotApproved");

    await l2.connect(client).applyToJoin();
    // round 0 -> InvalidRound
    await expect(l2.connect(client).uploadParameters(0, paramId, zero))
      .to.be.revertedWithCustomError(l2, "InvalidRound");
    // paramId 全零 -> InvalidParamId
    await expect(l2.connect(client).uploadParameters(1, zero, zero))
      .to.be.revertedWithCustomError(l2, "InvalidParamId");

    // 同客户端同轮二次上传 -> AlreadyUploaded
    await l2.connect(client).uploadParameters(1, paramId, zero);
    await expect(l2.connect(client).uploadParameters(1, ethers.keccak256(ethers.toUtf8Bytes("other")), zero))
      .to.be.revertedWithCustomError(l2, "AlreadyUploaded");

    // 另一客户端登记同一 paramId -> ParamIdTaken（内容 id 全局唯一）
    await l2.connect(owner).applyToJoin();
    await expect(l2.connect(owner).uploadParameters(1, paramId, zero))
      .to.be.revertedWithCustomError(l2, "ParamIdTaken");
  });

  it("view getters return initial state", async function () {
    const rec = await l2.getClient(client.address);
    expect(rec.round).to.equal(0);
    expect(rec.status).to.equal(0); // NONE
    expect(rec.paramHash).to.equal(ethers.ZeroHash);

    const pRec = await l2.getByParamId(ethers.ZeroHash);
    expect(pRec.client).to.equal(ethers.ZeroAddress);

    const round = await l1.getRound(1);
    expect(round.round).to.equal(0);

    expect(await l1.latestRound()).to.equal(0);
    expect(await l1.owner()).to.equal(owner.address);
    expect(await l2.owner()).to.equal(owner.address);
  });
});
