# CodeAlpha Blockchain Development Internship
## Tasks 2, 3 & 4 — Solidity Smart Contracts

> **Compiler:** Solidity `^0.8.20`  
> **IDE:** Remix IDE (remix.ethereum.org)  
> **Network:** Remix VM (for testing) / Sepolia testnet (for deployment)

---

## 📁 File Overview

| File | Task | Contract |
|------|------|----------|
| `MultiSend.sol` | Task 2 | Distributes ETH equally to multiple addresses |
| `PollingSystem.sol` | Task 3 | On-chain polling with time-locks & double-vote prevention |
| `CryptoLock.sol` | Task 4 | Personal ETH vault with configurable time-lock |

---

## ✅ Task 2 — MultiSend.sol

### What It Does
Accepts ETH and distributes it **equally** across an array of recipient addresses in a single transaction.

### Key Functions

| Function | Description |
|----------|-------------|
| `sendToAll(address[] recipients)` | **payable** — splits `msg.value` equally to all addresses |
| `previewShare(totalValue, numRecipients)` | View — shows per-address share + dust before sending |
| `rescueDust()` | Owner only — withdraws rounding remainders |
| `contractBalance()` | View — current ETH balance in contract |

### How to Test in Remix
1. Deploy `MultiSend.sol` (no constructor args)
2. Copy 3 test addresses from Remix's account list
3. In `sendToAll`, paste addresses as `["0xAddr1","0xAddr2","0xAddr3"]`
4. Set **Value** to e.g. `300000000000000000` wei (0.3 ETH)
5. Click **Transact** → each address should receive `0.1 ETH`
6. Check balances in the Remix accounts panel to confirm

### Design Decisions
- Uses `call{value: ...}` instead of deprecated `transfer()` — compatible with contract recipients
- Limits to 200 recipients to prevent block gas-limit issues
- `receive()` rejects plain ETH — forces use of `sendToAll()` to prevent accidental locks

---

## ✅ Task 3 — PollingSystem.sol

### What It Does
A fully decentralized polling system where any wallet can:
- Create polls with a title, answer options, and a deadline
- Vote once per poll (double-vote prevention via mapping)
- Query results and get the winner after the poll closes

### Key Functions

| Function | Description |
|----------|-------------|
| `createPoll(title, options[], durationInSeconds)` | Create a new poll; returns `pollId` |
| `vote(pollId, optionIndex)` | Cast one vote before the deadline |
| `getWinner(pollId)` | Returns winning option after poll ends |
| `getPoll(pollId)` | View all metadata for a poll |
| `getOptionVotes(pollId, optionIndex)` | View vote count for one option |
| `getAllVoteCounts(pollId)` | View all option counts at once |
| `hasVoted(pollId, voter)` | Check if an address has voted |
| `timeRemaining(pollId)` | Seconds until poll closes |
| `totalPolls()` | Total polls created so far |

### How to Test in Remix
1. Deploy `PollingSystem.sol`
2. Call `createPoll` with:
   - title: `"Best blockchain platform?"`
   - options: `["Ethereum","Solana","Avalanche"]`
   - durationInSeconds: `300` (5 minutes)
3. Note the returned `pollId` (should be `1`)
4. From **Account A**: `vote(1, 0)` → votes for Ethereum
5. From **Account B**: `vote(1, 1)` → votes for Solana
6. Try voting again from Account A → should revert with `"you have already voted"`
7. After deadline, call `getWinner(1)` → returns Ethereum (1 vote vs 1 — tie goes to lowest index)

### Design Decisions
- Polls are indexed from 1 (not 0) to distinguish "no poll" from "poll 1"
- Options stored as `string[]` in a struct — readable without off-chain decoding
- `getWinner()` emits a `PollResult` event so front-ends can index results easily
- Max 10 options per poll prevents excessive storage costs

---

## ✅ Task 4 — CryptoLock.sol

### What It Does
A personal crypto vault where users deposit ETH with a self-chosen lock duration. Withdrawal is **blocked** until `block.timestamp >= unlockTime`.

### Key Functions

| Function | Description |
|----------|-------------|
| `deposit(lockDurationInSeconds)` | **payable** — lock ETH for chosen duration |
| `withdraw()` | Withdraw full balance (only after unlock time) |
| `getVault(address)` | View any address's vault details |
| `myVault()` | Shorthand to view your own vault |
| `contractBalance()` | Total ETH currently locked in contract |
| `secondsToTime(secs)` | Helper — converts seconds to d/h/m/s |
| `pauseDeposits()` / `resumeDeposits()` | Owner emergency controls |

### How to Test in Remix
1. Deploy `CryptoLock.sol`
2. Set **Value** to `1000000000000000000` (1 ETH), call `deposit(120)` → locked for 2 minutes
3. Immediately call `withdraw()` → should revert `"still locked — come back later"`
4. Call `myVault()` → confirms `amount`, `unlockTime`, `secondsLeft`
5. In Remix VM, advance time: click the clock icon or wait 2 minutes
6. Call `withdraw()` → should succeed; ETH returns to your account
7. Test top-up: `deposit(300)` again, then `deposit(600)` → lock extends to the later time

### Design Decisions
- **Checks-Effects-Interactions** pattern — vault is zeroed out before the ETH transfer to prevent re-entrancy
- Top-up never shortens an existing lock (protects the user's savings intent)
- `receive()` rejects direct ETH to force use of `deposit()` with an explicit lock duration
- Owner **cannot** touch user funds — `pauseDeposits` only blocks new deposits

---

## 🔐 Security Notes (common to all contracts)

- No `transfer()` or `send()` — all ETH moves use `call{value:...}` with success checks
- Re-entrancy guarded via **Checks-Effects-Interactions** in `CryptoLock`
- Integer overflow impossible — Solidity 0.8.x has built-in overflow protection
- No floating-point — all amounts in wei (uint256)
- Zero address checks where applicable

---

## 🧪 Recommended Test Sequence (Remix)

```
1. Open remix.ethereum.org
2. Create a new workspace
3. Upload / paste each .sol file
4. Compile: Solidity compiler tab → set version 0.8.20 → Compile
5. Deploy: Deploy & Run tab → Environment: "Remix VM (Cancun)"
6. Follow per-contract test steps above
```
