import random
import os
import time

# ── ANSI color codes (works on most terminals) ──────────────────────────────
class Color:
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"

def c(text, color):
    return f"{color}{text}{Color.RESET}"

# ── Word bank with categories ────────────────────────────────────────────────
WORD_BANK = {
    "Animals":     ["elephant", "giraffe", "penguin", "crocodile", "butterfly"],
    "Countries":   ["brazil", "japan", "australia", "germany", "argentina"],
    "Technology":  ["algorithm", "keyboard", "database", "framework", "compiler"],
    "Sports":      ["basketball", "volleyball", "swimming", "gymnastics", "cricket"],
    "Foods":       ["spaghetti", "chocolate", "avocado", "blueberry", "cinnamon"],
}

# ── Hangman ASCII art (stages 0–6) ──────────────────────────────────────────
HANGMAN_STAGES = [
    # 0 wrong guesses
    """
  +---+
  |   |
      |
      |
      |
      |
=========
""",
    # 1
    """
  +---+
  |   |
  O   |
      |
      |
      |
=========
""",
    # 2
    """
  +---+
  |   |
  O   |
  |   |
      |
      |
=========
""",
    # 3
    """
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========
""",
    # 4
    """
  +---+
  |   |
  O   |
 /|\\  |
      |
      |
=========
""",
    # 5
    """
  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
=========
""",
    # 6 — dead
    """
  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
=========
""",
]

MAX_WRONG = 6

# ── Helper: clear screen ─────────────────────────────────────────────────────
def clear():
    os.system("cls" if os.name == "nt" else "clear")

# ── Display the current game state ───────────────────────────────────────────
def display_state(category, word, guessed, wrong_letters, score, hint_used):
    clear()
    print(c("=" * 50, Color.CYAN))
    print(c("        ☠  HANGMAN  ☠", Color.BOLD + Color.MAGENTA))
    print(c("=" * 50, Color.CYAN))
    print(f"  Category : {c(category, Color.YELLOW)}")
    print(f"  Score    : {c(str(score), Color.GREEN)}")
    print(f"  Hint used: {c('Yes' if hint_used else 'No', Color.YELLOW)}")
    print()

    # Gallows — color it red when near death
    stage_color = Color.RED if len(wrong_letters) >= 4 else Color.YELLOW
    print(c(HANGMAN_STAGES[len(wrong_letters)], stage_color))

    # Word display
    display_word = "  ".join(
        c(letter.upper(), Color.GREEN) if letter in guessed else c("_", Color.BOLD)
        for letter in word
    )
    print(f"  Word: {display_word}")
    print()

    # Wrong guesses
    if wrong_letters:
        wrong_str = "  ".join(c(l.upper(), Color.RED) for l in sorted(wrong_letters))
        print(f"  Wrong guesses ({len(wrong_letters)}/{MAX_WRONG}): {wrong_str}")
    else:
        print(f"  Wrong guesses: {c('None yet!', Color.GREEN)}")

    print()
    remaining = MAX_WRONG - len(wrong_letters)
    print(f"  {c(str(remaining), Color.RED if remaining <= 2 else Color.YELLOW)} guess(es) remaining")
    print(c("-" * 50, Color.CYAN))

# ── Choose difficulty ─────────────────────────────────────────────────────────
def choose_difficulty():
    print(c("\n  Select difficulty:", Color.BOLD))
    print(f"  {c('1', Color.GREEN)} Easy   — word length ≤ 6 letters")
    print(f"  {c('2', Color.YELLOW)} Medium — word length 7–9 letters")
    print(f"  {c('3', Color.RED)} Hard   — word length ≥ 10 letters")
    while True:
        choice = input(c("\n  Enter 1 / 2 / 3: ", Color.CYAN)).strip()
        if choice in ("1", "2", "3"):
            return int(choice)
        print(c("  Invalid choice, try again.", Color.RED))

# ── Pick a word matching the difficulty ──────────────────────────────────────
def pick_word(difficulty):
    all_words = [(word, cat) for cat, words in WORD_BANK.items() for word in words]
    if difficulty == 1:
        pool = [(w, c) for w, c in all_words if len(w) <= 6]
    elif difficulty == 2:
        pool = [(w, c) for w, c in all_words if 7 <= len(w) <= 9]
    else:
        pool = [(w, c) for w, c in all_words if len(w) >= 10]

    if not pool:          # fallback if pool is empty
        pool = all_words
    word, category = random.choice(pool)
    return word, category

# ── Give a hint (reveal one random unguessed letter) ─────────────────────────
def give_hint(word, guessed):
    unrevealed = [l for l in word if l not in guessed]
    if not unrevealed:
        return None
    hint_letter = random.choice(unrevealed)
    guessed.add(hint_letter)
    return hint_letter

# ── Calculate score ───────────────────────────────────────────────────────────
def calculate_score(wrong_count, word_length, hint_used, difficulty):
    base  = word_length * 10
    bonus = (MAX_WRONG - wrong_count) * 5 * difficulty
    penalty = 20 if hint_used else 0
    return max(0, base + bonus - penalty)

# ── Single game round ─────────────────────────────────────────────────────────
def play_round(difficulty):
    word, category = pick_word(difficulty)
    guessed       = set()
    wrong_letters = set()
    hint_used     = False
    score         = 0

    while True:
        display_state(category, word, guessed, wrong_letters, score, hint_used)

        # Win check
        if all(l in guessed for l in word):
            score = calculate_score(len(wrong_letters), len(word), hint_used, difficulty)
            print(c(f"\n  🎉  You won!  The word was: {word.upper()}", Color.GREEN + Color.BOLD))
            print(c(f"  Score this round: {score}", Color.YELLOW))
            return score, True

        # Lose check
        if len(wrong_letters) >= MAX_WRONG:
            print(c(f"\n  💀  Game over!  The word was: {word.upper()}", Color.RED + Color.BOLD))
            return 0, False

        prompt = c("  Your guess (letter) or 'hint' / 'quit': ", Color.CYAN)
        user_input = input(prompt).strip().lower()

        if user_input == "quit":
            print(c(f"\n  You quit. The word was: {word.upper()}", Color.YELLOW))
            return 0, False

        if user_input == "hint":
            if hint_used:
                print(c("  You already used your hint!", Color.RED))
                time.sleep(1)
                continue
            letter = give_hint(word, guessed)
            if letter:
                print(c(f"  💡 Hint: '{letter.upper()}' has been revealed!", Color.YELLOW))
                hint_used = True
                time.sleep(1.2)
            continue

        if len(user_input) != 1 or not user_input.isalpha():
            print(c("  Please enter a single letter.", Color.RED))
            time.sleep(1)
            continue

        if user_input in guessed or user_input in wrong_letters:
            print(c(f"  You already guessed '{user_input.upper()}'!", Color.YELLOW))
            time.sleep(1)
            continue

        if user_input in word:
            guessed.add(user_input)
            print(c(f"  ✅  '{user_input.upper()}' is in the word!", Color.GREEN))
        else:
            wrong_letters.add(user_input)
            print(c(f"  ❌  '{user_input.upper()}' is NOT in the word.", Color.RED))
        time.sleep(0.6)

# ── Main game loop ────────────────────────────────────────────────────────────
def main():
    clear()
    print(c("""
  ██╗  ██╗ █████╗ ███╗  ██╗ ██████╗ ███╗   ███╗ █████╗ ███╗  ██╗
  ██║  ██║██╔══██╗████╗ ██║██╔════╝ ████╗ ████║██╔══██╗████╗ ██║
  ███████║███████║██╔██╗██║██║  ███╗██╔████╔██║███████║██╔██╗██║
  ██╔══██║██╔══██║██║╚████║██║   ██║██║╚██╔╝██║██╔══██║██║╚████║
  ██║  ██║██║  ██║██║ ╚███║╚██████╔╝██║ ╚═╝ ██║██║  ██║██║ ╚███║
  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚══╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚══╝
    """, Color.MAGENTA + Color.BOLD))
    print(c("  Welcome! Guess the hidden word before the man hangs.", Color.CYAN))
    print(c("  Type 'hint' once per round to reveal a letter (costs points).\n", Color.CYAN))

    total_score = 0
    rounds_won  = 0
    round_num   = 0

    while True:
        difficulty = choose_difficulty()
        round_num += 1
        print(c(f"\n  ── Round {round_num} ──\n", Color.BOLD))
        time.sleep(0.5)

        round_score, won = play_round(difficulty)
        total_score += round_score
        if won:
            rounds_won += 1

        print(c(f"\n  Total score so far: {total_score}  |  Rounds won: {rounds_won}/{round_num}", Color.MAGENTA))

        again = input(c("\n  Play again? (y / n): ", Color.CYAN)).strip().lower()
        if again != "y":
            break

    print(c(f"\n  ══ Final Score: {total_score}  |  Rounds Won: {rounds_won}/{round_num} ══", Color.BOLD + Color.GREEN))
    print(c("  Thanks for playing Hangman! Goodbye.\n", Color.CYAN))


if __name__ == "__main__":
    main()