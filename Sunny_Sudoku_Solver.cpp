#include <iostream>
#include <vector>
#include <chrono>

using namespace std;

const int SIZE = 9;

// ----------------------------------------------
//  Display the board with box borders
// ----------------------------------------------
void printBoard(const int board[SIZE][SIZE]) {
    cout << "\n  +-----------------------+\n";
    for (int r = 0; r < SIZE; r++) {
        if (r == 3 || r == 6)
            cout << "  +-------+-------+-------¦\n";
        cout << "  ¦";
        for (int c = 0; c < SIZE; c++) {
            if (c == 3 || c == 6) cout << " ¦";
            if (board[r][c] == 0)
                cout << " .";
            else
                cout << " " << board[r][c];
        }
        cout << " ¦\n";
    }
    cout << "  +-----------------------+\n";
}

// ----------------------------------------------
//  Check if placing `num` at (row, col) is legal
// ----------------------------------------------
bool isSafe(const int board[SIZE][SIZE], int row, int col, int num) {
    // Row check
    for (int c = 0; c < SIZE; c++)
        if (board[row][c] == num) return false;

    // Column check
    for (int r = 0; r < SIZE; r++)
        if (board[r][col] == num) return false;

    // 3×3 subgrid check
    int startRow = (row / 3) * 3;
    int startCol = (col / 3) * 3;
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 3; c++)
            if (board[startRow + r][startCol + c] == num) return false;

    return true;
}

// ----------------------------------------------
//  Backtracking solver
// ----------------------------------------------
bool solve(int board[SIZE][SIZE]) {
    for (int row = 0; row < SIZE; row++) {
        for (int col = 0; col < SIZE; col++) {
            if (board[row][col] == 0) {
                for (int num = 1; num <= 9; num++) {
                    if (isSafe(board, row, col, num)) {
                        board[row][col] = num;
                        if (solve(board)) return true;
                        board[row][col] = 0; // backtrack
                    }
                }
                return false; // no valid number found
            }
        }
    }
    return true; // all cells filled
}

// ----------------------------------------------
//  Basic validation of the initial puzzle
// ----------------------------------------------
bool isValidPuzzle(const int board[SIZE][SIZE]) {
    for (int r = 0; r < SIZE; r++) {
        for (int c = 0; c < SIZE; c++) {
            int val = board[r][c];
            if (val < 0 || val > 9) return false;
            if (val != 0) {
                // Temporarily remove to check for duplicates
                int temp[SIZE][SIZE];
                for (int i = 0; i < SIZE; i++)
                    for (int j = 0; j < SIZE; j++)
                        temp[i][j] = board[i][j];
                temp[r][c] = 0;
                if (!isSafe(temp, r, c, val)) return false;
            }
        }
    }
    return true;
}

// ----------------------------------------------
//  Input the puzzle row by row
// ----------------------------------------------
void inputPuzzle(int board[SIZE][SIZE]) {
    cout << "\n  Enter the puzzle row by row.\n";
    cout << "  Use 0 (zero) for empty cells.\n";
    cout << "  Separate digits with spaces.\n\n";

    for (int r = 0; r < SIZE; r++) {
        while (true) {
            cout << "  Row " << (r + 1) << ": ";
            bool valid = true;
            for (int c = 0; c < SIZE; c++) {
                cin >> board[r][c];
                if (board[r][c] < 0 || board[r][c] > 9) valid = false;
            }
            if (valid) break;
            cout << "  ? Invalid input. Digits must be 0-9. Re-enter this row.\n";
        }
    }
}

// ----------------------------------------------
//  Built-in demo puzzle (hard level)
// ----------------------------------------------
void loadDemo(int board[SIZE][SIZE]) {
    int demo[SIZE][SIZE] = {
        {5, 3, 0,  0, 7, 0,  0, 0, 0},
        {6, 0, 0,  1, 9, 5,  0, 0, 0},
        {0, 9, 8,  0, 0, 0,  0, 6, 0},

        {8, 0, 0,  0, 6, 0,  0, 0, 3},
        {4, 0, 0,  8, 0, 3,  0, 0, 1},
        {7, 0, 0,  0, 2, 0,  0, 0, 6},

        {0, 6, 0,  0, 0, 0,  2, 8, 0},
        {0, 0, 0,  4, 1, 9,  0, 0, 5},
        {0, 0, 0,  0, 8, 0,  0, 7, 9}
    };
    for (int r = 0; r < SIZE; r++)
        for (int c = 0; c < SIZE; c++)
            board[r][c] = demo[r][c];
}

int main() {
    cout << "\n  ==========================================\n";
    cout << "       SUDOKU SOLVER \n";
    cout << "  ==========================================\n";

    int board[SIZE][SIZE] = {};
    int choice;

    cout << "\n  1. Enter puzzle manually\n";
    cout << "  2. Use built-in demo puzzle\n";
    cout << "  Choice: ";
    cin >> choice;

    if (choice == 1) {
        inputPuzzle(board);
        if (!isValidPuzzle(board)) {
            cout << "\n  ? The puzzle contains conflicts. Please check your input.\n\n";
            return 1;
        }
    } else {
        loadDemo(board);
    }

    cout << "\n  Puzzle (unsolved):";
    printBoard(board);

    // Solve and measure time
    auto start = chrono::high_resolution_clock::now();
    bool solved = solve(board);
    auto end   = chrono::high_resolution_clock::now();
    double ms  = chrono::duration<double, milli>(end - start).count();

    if (solved) {
        cout << "\n  ? Solved in " << ms << " ms!\n";
        cout << "\n  Solution:";
        printBoard(board);
    } else {
        cout << "\n  ? No solution exists for this puzzle.\n";
    }

    cout << "\n";
    return 0;
}
