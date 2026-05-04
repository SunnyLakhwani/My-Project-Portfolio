#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -------- Constants -------- */
#define FILE_NAME  "students.dat"
#define NAME_LEN   50
#define DEPT_LEN   30

/* -------- Data Structure -------- */
typedef struct {
    int    roll;
    char   name[NAME_LEN];
    char   dept[DEPT_LEN];
    float  cgpa;
    int    age;
} Student;

/* -------- Utility -------- */

/* Clears trailing newline / extra input */
void flush_input() {
    int c;
    while ((c = getchar()) != '\n' && c != EOF);
}

/* Prints a styled divider */
void divider(char ch, int len) {
	int i;
    for (i = 0; i < len; i++)
        putchar(ch);
    putchar('\n');
}

/* Checks if a roll number already exists in the file */
int roll_exists(int roll) {
    FILE *fp = fopen(FILE_NAME, "rb");
    if (!fp) return 0;

    Student s;
    while (fread(&s, sizeof(Student), 1, fp))
        if (s.roll == roll) { fclose(fp); return 1; }

    fclose(fp);
    return 0;
}

/* Counts total records in the file */
int count_records() {
    FILE *fp = fopen(FILE_NAME, "rb");
    if (!fp) return 0;

    int count = 0;
    Student s;
    while (fread(&s, sizeof(Student), 1, fp)) count++;
    fclose(fp);
    return count;
}

/* -------- Print a single student row -------- */
void print_header() {
    printf("\n");
    divider('-', 72);
    printf("  %-6s  %-20s  %-14s  %-6s  %-4s\n",
           "Roll", "Name", "Department", "CGPA", "Age");
    divider('-', 72);
}

void print_student(const Student *s) {
    printf("  %-6d  %-20s  %-14s  %-6.2f  %-4d\n",
           s->roll, s->name, s->dept, s->cgpa, s->age);
}

/* -------- FEATURE 1: Add Student -------- */
void add_student() {
    Student s;

    printf("\n  -- Add New Student --\n");

    printf("  Roll Number : ");
    if (scanf("%d", &s.roll) != 1 || s.roll <= 0) {
        printf("  [!] Invalid roll number.\n");
        flush_input();
        return;
    }
    flush_input();

    if (roll_exists(s.roll)) {
        printf("  [!] A student with Roll No. %d already exists.\n", s.roll);
        return;
    }

    printf("  Full Name   : ");
    fgets(s.name, NAME_LEN, stdin);
    s.name[strcspn(s.name, "\n")] = '\0';   /* strip newline */

    printf("  Department  : ");
    fgets(s.dept, DEPT_LEN, stdin);
    s.dept[strcspn(s.dept, "\n")] = '\0';

    printf("  CGPA (0-4)  : ");
    if (scanf("%f", &s.cgpa) != 1 || s.cgpa < 0.0f || s.cgpa > 4.0f) {
        printf("  [!] Invalid CGPA. Must be between 0.0 and 4.0.\n");
        flush_input();
        return;
    }

    printf("  Age         : ");
    if (scanf("%d", &s.age) != 1 || s.age <= 0) {
        printf("  [!] Invalid age.\n");
        flush_input();
        return;
    }
    flush_input();

    FILE *fp = fopen(FILE_NAME, "ab");
    if (!fp) { printf("  [!] Could not open file.\n"); return; }

    fwrite(&s, sizeof(Student), 1, fp);
    fclose(fp);

    printf("\n  [✓] Student '%s' added successfully.\n", s.name);
}

/* -------- FEATURE 2: Display All Students -------- */
void display_all() {
    FILE *fp = fopen(FILE_NAME, "rb");
    if (!fp) { printf("\n  [!] No records found. File does not exist yet.\n"); return; }

    Student s;
    int count = 0;

    printf("\n  ===== All Student Records =====");
    print_header();

    while (fread(&s, sizeof(Student), 1, fp)) {
        print_student(&s);
        count++;
    }

    divider('-', 72);
    printf("  Total records: %d\n", count);
    fclose(fp);

    if (count == 0)
        printf("  (No records stored yet)\n");
}

/* -------- FEATURE 3: Search by Roll Number -------- */
void search_student() {
    int roll;
    printf("\n  -- Search Student --\n");
    printf("  Enter Roll Number to search: ");
    scanf("%d", &roll);
    flush_input();

    FILE *fp = fopen(FILE_NAME, "rb");
    if (!fp) { printf("  [!] No records found.\n"); return; }

    Student s;
    int found = 0;

    while (fread(&s, sizeof(Student), 1, fp)) {
        if (s.roll == roll) {
            printf("\n  [✓] Student Found:");
            print_header();
            print_student(&s);
            divider('-', 72);
            found = 1;
            break;
        }
    }

    fclose(fp);
    if (!found)
        printf("  [!] No student found with Roll No. %d.\n", roll);
}

/* -------- FEATURE 4: Update Student Record -------- */
void update_student() {
    int roll;
    printf("\n  -- Update Student Record --\n");
    printf("  Enter Roll Number to update: ");
    scanf("%d", &roll);
    flush_input();

    FILE *fp = fopen(FILE_NAME, "rb+");
    if (!fp) { printf("  [!] No records found.\n"); return; }

    Student s;
    int found = 0;

    while (fread(&s, sizeof(Student), 1, fp)) {
        if (s.roll == roll) {
            found = 1;

            printf("  Current Name   : %s\n", s.name);
            printf("  New Name (Enter to keep): ");
            char tmp[NAME_LEN];
            fgets(tmp, NAME_LEN, stdin);
            tmp[strcspn(tmp, "\n")] = '\0';
            if (strlen(tmp) > 0) strcpy(s.name, tmp);

            printf("  Current Dept   : %s\n", s.dept);
            printf("  New Department (Enter to keep): ");
            fgets(tmp, DEPT_LEN, stdin);
            tmp[strcspn(tmp, "\n")] = '\0';
            if (strlen(tmp) > 0) strcpy(s.dept, tmp);

            printf("  Current CGPA   : %.2f\n", s.cgpa);
            printf("  New CGPA (-1 to keep): ");
            float new_cgpa;
            scanf("%f", &new_cgpa);
            flush_input();
            if (new_cgpa >= 0.0f && new_cgpa <= 4.0f)
                s.cgpa = new_cgpa;

            printf("  Current Age    : %d\n", s.age);
            printf("  New Age (0 to keep): ");
            int new_age;
            scanf("%d", &new_age);
            flush_input();
            if (new_age > 0) s.age = new_age;

            /* Move file pointer back one record and overwrite */
            fseek(fp, -(long)sizeof(Student), SEEK_CUR);
            fwrite(&s, sizeof(Student), 1, fp);

            printf("\n  [✓] Record updated successfully.\n");
            break;
        }
    }

    fclose(fp);
    if (!found)
        printf("  [!] No student found with Roll No. %d.\n", roll);
}

/* -------- FEATURE 5: Delete Student -------- */
void delete_student() {
    int roll;
    printf("\n  -- Delete Student Record --\n");
    printf("  Enter Roll Number to delete: ");
    scanf("%d", &roll);
    flush_input();

    FILE *fp = fopen(FILE_NAME, "rb");
    if (!fp) { printf("  [!] No records found.\n"); return; }

    /* Read all records, skip the one to delete */
    Student all[500];
    int count = 0, found = 0;
    Student s;

    while (fread(&s, sizeof(Student), 1, fp)) {
        if (s.roll == roll) {
            found = 1;
            printf("  Deleting: %s (Roll %d)\n", s.name, s.roll);
        } else {
            all[count++] = s;
        }
    }
    fclose(fp);

    if (!found) {
        printf("  [!] No student found with Roll No. %d.\n", roll);
        return;
    }

    /* Confirm deletion */
    char confirm;
    printf("  Are you sure? (y/n): ");
    scanf(" %c", &confirm);
    flush_input();

    if (confirm != 'y' && confirm != 'Y') {
        printf("  Deletion cancelled.\n");
        return;
    }

    /* Write remaining records back */
    FILE *fw = fopen(FILE_NAME, "wb");
    if (!fw) { printf("  [!] Could not write file.\n"); return; }
    
	int i;
    for (i = 0; i < count; i++)
        fwrite(&all[i], sizeof(Student), 1, fw);

    fclose(fw);
    printf("  [✓] Record deleted. Total records remaining: %d\n", count);
}

/* -------- Main -------- */
int main() {
    int choice;
    char again;

    printf("\n");
    divider('=', 50);
    printf("    CodeAlpha — Student Management System\n");
    divider('=', 50);
    printf("  Records file: %s\n", FILE_NAME);
    printf("  Total records loaded: %d\n", count_records());

    do {
        printf("\n");
        divider('-', 40);
        printf("  MENU\n");
        divider('-', 40);
        printf("  1. Add Student\n");
        printf("  2. Display All Students\n");
        printf("  3. Search Student (by Roll No.)\n");
        printf("  4. Update Student Record\n");
        printf("  5. Delete Student Record\n");
        printf("  6. Exit\n");
        divider('-', 40);
        printf("  Choice: ");
        scanf("%d", &choice);
        flush_input();

        switch (choice) {
            case 1: add_student();     break;
            case 2: display_all();     break;
            case 3: search_student();  break;
            case 4: update_student();  break;
            case 5: delete_student();  break;
            case 6:
                printf("\n  Goodbye! All records saved to '%s'.\n\n", FILE_NAME);
                return 0;
            default:
                printf("  [!] Invalid option. Please select 1–6.\n");
        }

        printf("\n  Return to main menu? (y/n): ");
        scanf(" %c", &again);
        flush_input();

    } while (again == 'y' || again == 'Y');

    printf("\n  Session ended. Data is saved.\n\n");
    return 0;
}
