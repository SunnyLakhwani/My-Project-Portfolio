// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PollingSystem
 * @author Sunny Lakhwani
 * @notice A decentralized, on-chain polling system where anyone can create
 *         polls and vote — with time-based restrictions and double-vote prevention.
 *
 * FEATURES:
 *  - Anyone can create a poll with a title, up to 10 options, and a deadline
 *  - Each Ethereum address can vote exactly once per poll, before the deadline
 *  - Results and the winning option are queryable after the poll ends
 *  - Polls are stored by incrementing IDs — easy to enumerate
 */
contract PollingSystem {

    // ── Constants ────────────────────────────────────────────────────────────

    uint256 public constant MAX_OPTIONS  = 10;
    uint256 public constant MIN_DURATION = 60;        // at least 1 minute
    uint256 public constant MAX_DURATION = 30 days;

    // ── Structs ──────────────────────────────────────────────────────────────

    struct Poll {
        uint256  id;
        address  creator;
        string   title;
        string[] options;        // the text of each option
        uint256  endTime;        // Unix timestamp when voting closes
        uint256  totalVotes;     // convenience counter
        bool     exists;         // guard for invalid poll IDs
    }

    // ── State ────────────────────────────────────────────────────────────────

    uint256 private _nextPollId;   // auto-incrementing ID (starts at 1)

    // pollId => Poll
    mapping(uint256 => Poll) private _polls;

    // pollId => optionIndex => vote count
    mapping(uint256 => mapping(uint256 => uint256)) private _voteCounts;

    // pollId => voter address => has voted?
    mapping(uint256 => mapping(address => bool)) private _hasVoted;

    // ── Events ───────────────────────────────────────────────────────────────

    event PollCreated(
        uint256 indexed pollId,
        address indexed creator,
        string  title,
        uint256 endTime
    );

    event VoteCast(
        uint256 indexed pollId,
        address indexed voter,
        uint256         optionIndex,
        string          optionText
    );

    event PollResult(
        uint256 indexed pollId,
        uint256         winningIndex,
        string          winningOption,
        uint256         winningVotes
    );

    // ── Poll Creation ─────────────────────────────────────────────────────────

    /**
     * @notice Create a new poll
     * @param title            A short description / question for the poll
     * @param options          Array of answer choices (2–10 items)
     * @param durationInSeconds How long the poll stays open (60s – 30 days)
     * @return pollId          The ID of the newly created poll
     */
    function createPoll(
        string   calldata   title,
        string[] calldata   options,
        uint256             durationInSeconds
    )
        external
        returns (uint256 pollId)
    {
        require(bytes(title).length > 0,  "Poll: title cannot be empty");
        require(options.length >= 2,      "Poll: need at least 2 options");
        require(options.length <= MAX_OPTIONS, "Poll: too many options (max 10)");
        require(durationInSeconds >= MIN_DURATION, "Poll: duration too short (min 60s)");
        require(durationInSeconds <= MAX_DURATION, "Poll: duration too long (max 30 days)");

        // Validate that no option string is blank
        for (uint256 i = 0; i < options.length; i++) {
            require(bytes(options[i]).length > 0, "Poll: option text cannot be empty");
        }

        pollId = ++_nextPollId;   // IDs start at 1

        Poll storage p = _polls[pollId];
        p.id         = pollId;
        p.creator    = msg.sender;
        p.title      = title;
        p.endTime    = block.timestamp + durationInSeconds;
        p.totalVotes = 0;
        p.exists     = true;

        // Copy options into storage (dynamic string[] can't be set directly)
        for (uint256 i = 0; i < options.length; i++) {
            p.options.push(options[i]);
        }

        emit PollCreated(pollId, msg.sender, title, p.endTime);
    }

    // ── Voting ────────────────────────────────────────────────────────────────

    /**
     * @notice Cast a vote in an active poll
     * @param pollId      ID of the poll to vote in
     * @param optionIndex Zero-based index of your chosen option
     */
    function vote(uint256 pollId, uint256 optionIndex) external {
        Poll storage p = _polls[pollId];

        require(p.exists,                        "Poll: poll does not exist");
        require(block.timestamp < p.endTime,     "Poll: voting period has ended");
        require(!_hasVoted[pollId][msg.sender],  "Poll: you have already voted");
        require(optionIndex < p.options.length,  "Poll: invalid option index");

        // Record the vote
        _hasVoted[pollId][msg.sender] = true;
        _voteCounts[pollId][optionIndex]++;
        p.totalVotes++;

        emit VoteCast(pollId, msg.sender, optionIndex, p.options[optionIndex]);
    }

    // ── Results ───────────────────────────────────────────────────────────────

    /**
     * @notice Get the winning option after a poll has closed
     * @dev    In case of a tie, returns the option with the lowest index
     * @param pollId ID of the poll to query
     * @return winningIndex   Index of the winning option
     * @return winningOption  Text of the winning option
     * @return winningVotes   Number of votes it received
     */
    function getWinner(uint256 pollId)
        external
        returns (
            uint256 winningIndex,
            string memory winningOption,
            uint256 winningVotes
        )
    {
        Poll storage p = _polls[pollId];

        require(p.exists,                    "Poll: poll does not exist");
        require(block.timestamp >= p.endTime, "Poll: voting is still ongoing");
        require(p.totalVotes > 0,            "Poll: no votes were cast");

        uint256 highestVotes = 0;
        uint256 winIdx       = 0;

        for (uint256 i = 0; i < p.options.length; i++) {
            if (_voteCounts[pollId][i] > highestVotes) {
                highestVotes = _voteCounts[pollId][i];
                winIdx       = i;
            }
        }

        winningIndex  = winIdx;
        winningOption = p.options[winIdx];
        winningVotes  = highestVotes;

        emit PollResult(pollId, winningIndex, winningOption, winningVotes);
    }

    // ── View / Read Functions ─────────────────────────────────────────────────

    /**
     * @notice Fetch the core metadata of a poll
     */
    function getPoll(uint256 pollId)
        external
        view
        returns (
            address  creator,
            string   memory title,
            string[] memory options,
            uint256  endTime,
            uint256  totalVotes,
            bool     isActive
        )
    {
        Poll storage p = _polls[pollId];
        require(p.exists, "Poll: poll does not exist");

        creator    = p.creator;
        title      = p.title;
        options    = p.options;
        endTime    = p.endTime;
        totalVotes = p.totalVotes;
        isActive   = block.timestamp < p.endTime;
    }

    /**
     * @notice Get the current vote count for a specific option
     */
    function getOptionVotes(uint256 pollId, uint256 optionIndex)
        external
        view
        returns (uint256)
    {
        require(_polls[pollId].exists, "Poll: poll does not exist");
        require(optionIndex < _polls[pollId].options.length, "Poll: invalid option index");
        return _voteCounts[pollId][optionIndex];
    }

    /**
     * @notice Get all vote counts for every option in a poll
     */
    function getAllVoteCounts(uint256 pollId)
        external
        view
        returns (uint256[] memory counts)
    {
        Poll storage p = _polls[pollId];
        require(p.exists, "Poll: poll does not exist");

        counts = new uint256[](p.options.length);
        for (uint256 i = 0; i < p.options.length; i++) {
            counts[i] = _voteCounts[pollId][i];
        }
    }

    /**
     * @notice Check whether a specific address has already voted in a poll
     */
    function hasVoted(uint256 pollId, address voter) external view returns (bool) {
        require(_polls[pollId].exists, "Poll: poll does not exist");
        return _hasVoted[pollId][voter];
    }

    /**
     * @notice Returns the total number of polls created so far
     */
    function totalPolls() external view returns (uint256) {
        return _nextPollId;
    }

    /**
     * @notice Seconds remaining before a poll closes (0 if already ended)
     */
    function timeRemaining(uint256 pollId) external view returns (uint256) {
        Poll storage p = _polls[pollId];
        require(p.exists, "Poll: poll does not exist");
        if (block.timestamp >= p.endTime) return 0;
        return p.endTime - block.timestamp;
    }
}
