#include <stdio.h>
#include <stdlib.h>

#define MAX 10
void read_matrix(int rows, int cols, double mat[MAX][MAX], const char *name) {
	int i,j;
    printf("\n  Enter elements of Matrix %s (%d x %d):\n", name, rows, cols);
    for (i = 0; i < rows; i++) {
        for (j = 0; j < cols; j++) {
            printf("    %s[%d][%d]: ", name, i + 1, j + 1);
            scanf("%lf", &mat[i][j]);
        }
    }
}

/* Prints a matrix with a label */
void print_matrix(int rows, int cols, double mat[MAX][MAX], const char *label) {
	int i,j;
    printf("\n  %s:\n", label);
    printf("  ");
    for (j = 0; j < cols; j++) printf("----------");
    printf("\n");

    for (i = 0; i < rows; i++) {
        printf("  | ");
        for (j = 0; j < cols; j++) {
            printf("%7.2lf ", mat[i][j]);
        }
        printf("|\n");
    }

    printf("  ");
    for (j = 0; j < cols; j++) printf("----------");
    printf("\n");
}

/* ---------- Core Operations ---------- */

/* Adds two matrices of the same size */
void matrix_add(int rows, int cols,
                double A[MAX][MAX], double B[MAX][MAX], double C[MAX][MAX]) {
                	int i,j;
    for (i = 0; i < rows; i++)
        for (j = 0; j < cols; j++)
            C[i][j] = A[i][j] + B[i][j];
}

/* Multiplies A (r1 x c1) by B (c1 x c2) into C (r1 x c2) */
void matrix_multiply(int r1, int c1, int c2,
                     double A[MAX][MAX], double B[MAX][MAX], double C[MAX][MAX]) {
                     	int i,j,k;
    /* Zero out result matrix first */
    for (i = 0; i < r1; i++)
        for (j = 0; j < c2; j++)
            C[i][j] = 0;

    for (i = 0; i < r1; i++)
        for (j = 0; j < c2; j++)
            for (k = 0; k < c1; k++)
                C[i][j] += A[i][k] * B[k][j];
}

/* Transposes matrix A (r x c) into T (c x r) */
void matrix_transpose(int rows, int cols,
                      double A[MAX][MAX], double T[MAX][MAX]) {
                      	int i,j;
    for (i = 0; i < rows; i++)
        for (j = 0; j < cols; j++)
            T[j][i] = A[i][j];
}

/* ---------- Menu Handlers ---------- */

void do_addition() {
    int rows, cols;
    double A[MAX][MAX], B[MAX][MAX], C[MAX][MAX];

    printf("\n  -- Matrix Addition --\n");
    printf("  Enter number of rows    (1-%d): ", MAX);
    scanf("%d", &rows);
    printf("  Enter number of columns (1-%d): ", MAX);
    scanf("%d", &cols);

    if (rows < 1 || rows > MAX || cols < 1 || cols > MAX) {
        printf("  [!] Dimensions out of range.\n");
        return;
    }

    read_matrix(rows, cols, A, "A");
    read_matrix(rows, cols, B, "B");

    matrix_add(rows, cols, A, B, C);

    print_matrix(rows, cols, A, "Matrix A");
    print_matrix(rows, cols, B, "Matrix B");
    print_matrix(rows, cols, C, "Result (A + B)");
}

void do_multiplication() {
    int r1, c1, r2, c2;
    double A[MAX][MAX], B[MAX][MAX], C[MAX][MAX];

    printf("\n  -- Matrix Multiplication --\n");
    printf("  Enter rows of Matrix A    (1-%d): ", MAX);
    scanf("%d", &r1);
    printf("  Enter columns of Matrix A (1-%d): ", MAX);
    scanf("%d", &c1);

    printf("  Enter rows of Matrix B    (must be %d): ", c1);
    scanf("%d", &r2);

    if (r2 != c1) {
        printf("  [!] Incompatible dimensions: columns of A must equal rows of B.\n");
        return;
    }

    printf("  Enter columns of Matrix B (1-%d): ", MAX);
    scanf("%d", &c2);

    if (r1 < 1 || r1 > MAX || c1 < 1 || c1 > MAX || c2 < 1 || c2 > MAX) {
        printf("  [!] Dimensions out of range.\n");
        return;
    }

    read_matrix(r1, c1, A, "A");
    read_matrix(r2, c2, B, "B");

    matrix_multiply(r1, c1, c2, A, B, C);

    print_matrix(r1, c1, A, "Matrix A");
    print_matrix(r2, c2, B, "Matrix B");
    print_matrix(r1, c2, C, "Result (A x B)");
}

void do_transpose() {
    int rows, cols;
    double A[MAX][MAX], T[MAX][MAX];

    printf("\n  -- Matrix Transpose --\n");
    printf("  Enter number of rows    (1-%d): ", MAX);
    scanf("%d", &rows);
    printf("  Enter number of columns (1-%d): ", MAX);
    scanf("%d", &cols);

    if (rows < 1 || rows > MAX || cols < 1 || cols > MAX) {
        printf("  [!] Dimensions out of range.\n");
        return;
    }

    read_matrix(rows, cols, A, "A");
    matrix_transpose(rows, cols, A, T);

    print_matrix(rows, cols, A, "Original Matrix A");
    print_matrix(cols, rows, T, "Transpose of A");
}

/* ---------- Main ---------- */

int main() {
    int choice;
    char again;

    printf("\n  Welcome to the CodeAlpha Matrix Calculator!\n");

    do {
        printf("\n=============================\n");
        printf("      MATRIX OPERATIONS      \n");
        printf("=============================\n");
        printf("  1. Matrix Addition\n");
        printf("  2. Matrix Multiplication\n");
        printf("  3. Matrix Transpose\n");
        printf("  4. Exit\n");
        printf("=============================\n");
        printf("  Your choice: ");
        
        scanf("%d", &choice);

        switch (choice) {
            case 1: do_addition();        break;
            case 2: do_multiplication();  break;
            case 3: do_transpose();       break;
            case 4:
                printf("\n  Exiting. Goodbye!\n\n");
                return 0;
            default:
                printf("  [!] Invalid choice. Try again.\n");
        }

        printf("\n  Perform another operation? (y/n): ");
        scanf(" %c", &again);

    } while (again == 'y' || again == 'Y');

    printf("\n  Session ended. Have a great day!\n\n");
    return 0;
}
