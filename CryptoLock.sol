// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title CryptoLock
 * @author Sunny Lakhwani
 * @notice A personal crypto-vault that time-locks Ether deposits.
 *         Users deposit ETH with a custom unlock time; withdrawals are blocked
 *         until that timestamp passes.
 */
contract CryptoLock {

    // ── Constants ────────────────────────────────────────────────────────────

    uint256 public constant MIN_LOCK_DURATION = 60;          // 1 minute
    uint256 public constant MAX_LOCK_DURATION = 5 * 365 days; // 5 years

    // ── Structs ──────────────────────────────────────────────────────────────

    struct VaultEntry {
        uint256 amount;        // total ETH locked (in wei)
        uint256 unlockTime;    // Unix timestamp when withdrawal is allowed
        uint256 depositCount;  // how many times this user has topped up
        bool    exists;        // guard — did this user ever deposit?
    }

    // ── State ────────────────────────────────────────────────────────────────

    address public immutable owner;
    bool    public  paused;        // deposit kill-switch (emergencies only)

    // user address => their vault
    mapping(address => VaultEntry) private _vaults;

    // cumulative stats
    uint256 public totalDeposited;
    uint256 public totalWithdrawn;
    uint256 public activeDepositors;

    // ── Events ───────────────────────────────────────────────────────────────

    event Deposited(
        address indexed user,
        uint256 amount,
        uint256 unlockTime,
        uint256 depositCount
    );

    event Withdrawn(
        address indexed user,
        uint256 amount,
        uint256 timestamp
    );

    event ContractPaused(address indexed by);
    event ContractUnpaused(address indexed by);

    // ── Modifiers ────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "CryptoLock: not the owner");
        _;
    }

    modifier notPaused() {
        require(!paused, "CryptoLock: deposits are currently paused");
        _;
    }

    // ── Constructor ──────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ── Deposit ───────────────────────────────────────────────────────────────

    
    function deposit(uint256 lockDurationInSeconds) external payable notPaused {
        require(msg.value > 0, "CryptoLock: must send ETH");
        require(
            lockDurationInSeconds >= MIN_LOCK_DURATION,
            "CryptoLock: lock too short (min 60 seconds)"
        );
        require(
            lockDurationInSeconds <= MAX_LOCK_DURATION,
            "CryptoLock: lock too long (max 5 years)"
        );

        uint256 newUnlockTime = block.timestamp + lockDurationInSeconds;
        VaultEntry storage vault = _vaults[msg.sender];

        if (!vault.exists) {
            // First-time depositor
            vault.exists      = true;
            vault.amount      = msg.value;
            vault.unlockTime  = newUnlockTime;
            vault.depositCount = 1;
            activeDepositors++;
        } else {
            // Top-up: add ETH and never shorten the existing lock
            vault.amount     += msg.value;
            vault.unlockTime  = newUnlockTime > vault.unlockTime
                                    ? newUnlockTime
                                    : vault.unlockTime;
            vault.depositCount++;
        }

        totalDeposited += msg.value;

        emit Deposited(
            msg.sender,
            msg.value,
            vault.unlockTime,
            vault.depositCount
        );
    }

    // ── Withdraw ──────────────────────────────────────────────────────────────

    /**
     * @notice Withdraw your full locked balance after the unlock time has passed
     * @dev    Follows Checks-Effects-Interactions pattern to prevent re-entrancy
     */
    function withdraw() external {
        VaultEntry storage vault = _vaults[msg.sender];

        require(vault.exists,           "CryptoLock: no deposit found");
        require(vault.amount > 0,       "CryptoLock: nothing to withdraw");
        require(
            block.timestamp >= vault.unlockTime,
            "CryptoLock: still locked — come back later"
        );

        uint256 payout = vault.amount;

        // Effects — zero out before external call (re-entrancy guard)
        vault.amount     = 0;
        vault.unlockTime = 0;
        vault.depositCount = 0;
        vault.exists     = false;
        activeDepositors--;
        totalWithdrawn  += payout;

        // Interaction
        (bool success, ) = msg.sender.call{value: payout}("");
        require(success, "CryptoLock: ETH transfer failed");

        emit Withdrawn(msg.sender, payout, block.timestamp);
    }

    // ── View / Read Functions ─────────────────────────────────────────────────

    /**
     * @notice Check the status of your vault (or any address)
     * @return amount        Locked ETH balance in wei
     * @return unlockTime    Unix timestamp when withdrawal opens
     * @return secondsLeft   Seconds until unlock (0 if already unlocked)
     * @return isUnlocked    True if withdrawal is currently allowed
     * @return depositCount  Number of deposits made to this vault
     */
    function getVault(address user)
        external
        view
        returns (
            uint256 amount,
            uint256 unlockTime,
            uint256 secondsLeft,
            bool    isUnlocked,
            uint256 depositCount
        )
    {
        VaultEntry storage vault = _vaults[user];

        amount       = vault.amount;
        unlockTime   = vault.unlockTime;
        depositCount = vault.depositCount;
        isUnlocked   = vault.exists && block.timestamp >= vault.unlockTime;
        secondsLeft  = (vault.exists && block.timestamp < vault.unlockTime)
                           ? vault.unlockTime - block.timestamp
                           : 0;
    }

    /**
     * @notice Shorthand to check your own vault status
     */
    function myVault()
        external
        view
        returns (
            uint256 amount,
            uint256 unlockTime,
            uint256 secondsLeft,
            bool    isUnlocked,
            uint256 depositCount
        )
    {
        return this.getVault(msg.sender);
    }

    /**
     * @notice Returns the total ETH currently locked in the contract
     */
    function contractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    /**
     * @notice Converts seconds into a human-readable breakdown
     * @dev    Purely a convenience helper for UIs / testing
     */
    function secondsToTime(uint256 secs)
        external
        pure
        returns (uint256 d, uint256 h, uint256 m, uint256 s)
    {
        d = secs / 86400;
        h = (secs % 86400) / 3600;
        m = (secs % 3600) / 60;
        s = secs % 60;
    }

    // ── Admin (Emergency Only) ────────────────────────────────────────────────

    /**
     * @notice Pause new deposits (existing locks and withdrawals are unaffected)
     * @dev    Only useful in a genuine emergency; cannot touch user funds
     */
    function pauseDeposits() external onlyOwner {
        require(!paused, "CryptoLock: already paused");
        paused = true;
        emit ContractPaused(msg.sender);
    }

    function resumeDeposits() external onlyOwner {
        require(paused, "CryptoLock: not paused");
        paused = false;
        emit ContractUnpaused(msg.sender);
    }

    // Reject direct ETH transfers — use deposit() instead
    receive() external payable {
        revert("CryptoLock: use deposit() to lock ETH");
    }
}
