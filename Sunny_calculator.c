#include <stdio.h>
#include <stdlib.h>

/* Clears input buffer to avoid leftover characters */
void flush_input() {
    int c;
    while ((c = getchar()) != '\n' && c != EOF);
}

/* Displays the calculator menu */
void show_menu() {
    printf("\n=============================\n");
    printf("      SIMPLE CALCULATOR      \n");
    printf("=============================\n");
    printf("  1. Addition       (+)\n");
    printf("  2. Subtraction    (-)\n");
    printf("  3. Multiplication (*)\n");
    printf("  4. Division       (/)\n");
    printf("  5. Exit\n");
    printf("=============================\n");
    printf("  Enter your choice: ");
}

int main() {
    int choice;
    double num1, num2, result;
    char again;

    printf("\n  Welcome to the CodeAlpha Calculator!\n");

    do {
        show_menu();

        /* Validate menu choice */
        if (scanf("%d", &choice) != 1) {
            printf("  [!] Invalid input. Please enter a number.\n");
            flush_input();
            continue;
        }
        flush_input();

        if (choice == 5) {
            printf("\n  Thank you for using the calculator. Goodbye!\n\n");
            break;
        }

        if (choice < 1 || choice > 4) {
            printf("  [!] Invalid choice. Please select between 1 and 5.\n");
            continue;
        }

        /* Read operands */
        printf("  Enter first number  : ");
        if (scanf("%lf", &num1) != 1) {
            printf("  [!] Invalid number entered.\n");
            flush_input();
            continue;
        }

        printf("  Enter second number : ");
        if (scanf("%lf", &num2) != 1) {
            printf("  [!] Invalid number entered.\n");
            flush_input();
            continue;
        }
        flush_input();

        /* Perform the selected operation */
        switch (choice) {
            case 1:
                result = num1 + num2;
                printf("\n  Result: %.2lf + %.2lf = %.2lf\n", num1, num2, result);
                break;

            case 2:
                result = num1 - num2;
                printf("\n  Result: %.2lf - %.2lf = %.2lf\n", num1, num2, result);
                break;

            case 3:
                result = num1 * num2;
                printf("\n  Result: %.2lf * %.2lf = %.2lf\n", num1, num2, result);
                break;

            case 4:
                if (num2 == 0) {
                    printf("\n  [!] Error: Division by zero is undefined.\n");
                } else {
                    result = num1 / num2;
                    printf("\n  Result: %.2lf / %.2lf = %.2lf\n", num1, num2, result);
                }
                break;
        }

        /* Ask if user wants to continue */
        printf("\n  Perform another calculation? (y/n): ");
        scanf(" %c", &again);
        flush_input();

    } while (again == 'y' || again == 'Y');

    printf("\n  Session ended. Have a great day!\n\n");
    return 0;
}
