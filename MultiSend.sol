// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MultiSend
 * @author Sunny Lakhwani
 * @notice Distributes Ether equally among a list of recipient addresses
 * @dev Accepts ETH via a payable function and splits it evenly across recipients
 */
contract MultiSend {

    // ── Events ──────────────────────────────────────────────────────────────

    /// @notice Fired once per recipient after each successful transfer
    event FundsSent(address indexed recipient, uint256 amount);

    /// @notice Fired when the owner rescues leftover dust (rounding remainders)
    event DustWithdrawn(address indexed to, uint256 amount);

    // ── State ────────────────────────────────────────────────────────────────

    address public immutable owner;

    // tracks total ETH ever distributed through the contract
    uint256 public totalDistributed;

    // ── Modifiers ────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "MultiSend: caller is not the owner");
        _;
    }

    // ── Constructor ──────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ── Core Logic ───────────────────────────────────────────────────────────

    /**
     * @notice Send equal shares of the attached ETH to every address in `recipients`
     * @dev    Any dust left over from integer division stays in the contract;
     *         the owner can withdraw it via rescueDust().
     *
     * @param recipients Array of wallet/contract addresses to receive ETH
     *
     * Requirements:
     *  - recipients must not be empty
     *  - recipients must have fewer than 200 entries (gas-limit safety)
     *  - msg.value must be divisible-ish — at least 1 wei per recipient
     *  - No zero addresses allowed
     */
    function sendToAll(address[] calldata recipients) external payable {
        uint256 count = recipients.length;

        require(count > 0,   "MultiSend: no recipients provided");
        require(count <= 200, "MultiSend: too many recipients (max 200)");
        require(msg.value > 0, "MultiSend: must send ETH with this call");

        uint256 sharePerRecipient = msg.value / count;

        require(sharePerRecipient > 0, "MultiSend: ETH too small to split");

        for (uint256 i = 0; i < count; i++) {
            address recipient = recipients[i];

            require(recipient != address(0), "MultiSend: zero address in list");

            // Using call() instead of transfer() — safer for contract recipients
            (bool success, ) = recipient.call{value: sharePerRecipient}("");
            require(success, "MultiSend: transfer failed");

            emit FundsSent(recipient, sharePerRecipient);
        }

        // Accumulate distributed amount (excluding dust)
        totalDistributed += sharePerRecipient * count;
    }

    /**
     * @notice Returns how much ETH 1 recipient would get for a given value
     *         and recipient count — useful for front-end previews
     *
     * @param totalValue   Amount of wei you plan to send
     * @param numRecipients Number of addresses
     * @return share       Wei each address would receive
     * @return dust        Leftover wei due to integer division
     */
    function previewShare(uint256 totalValue, uint256 numRecipients)
        external
        pure
        returns (uint256 share, uint256 dust)
    {
        require(numRecipients > 0, "MultiSend: division by zero");
        share = totalValue / numRecipients;
        dust  = totalValue % numRecipients;
    }

    /**
     * @notice Lets the owner withdraw any rounding dust that accumulated
     * @dev    This should normally be just a few wei
     */
    function rescueDust() external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "MultiSend: nothing to withdraw");

        (bool ok, ) = owner.call{value: balance}("");
        require(ok, "MultiSend: dust withdrawal failed");

        emit DustWithdrawn(owner, balance);
    }

    /// @notice Returns the current ETH balance sitting in the contract (dust only)
    function contractBalance() external view returns (uint256) {
        return address(this).balance;
    }

    // Reject plain ETH transfers not made through sendToAll
    receive() external payable {
        revert("MultiSend: use sendToAll() to send ETH");
    }
}
