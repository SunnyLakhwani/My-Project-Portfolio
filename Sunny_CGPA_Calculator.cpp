#include <iostream>
#include <iomanip>
#include <string>
#include <vector>

using namespace std;

// Converts letter grade to grade points
double gradeToPoints(const string& grade) {
    if (grade == "A+" || grade == "A") return 4.0;
    if (grade == "A-") return 3.7;
    if (grade == "B+") return 3.3;
    if (grade == "B") return 3.0;
    if (grade == "B-") return 2.7;
    if (grade == "C+") return 2.3;
    if (grade == "C") return 2.0;
    if (grade == "C-") return 1.7;
    if (grade == "D+") return 1.3;
    if (grade == "D") return 1.0;
    if (grade == "F") return 0.0;
    return -1;
}

struct Course {
    string name;
    string grade;
    double gradePoints;
    int creditHours;
};

void displaySummary(const vector<Course>& courses, double cgpa) {
    cout << "\n";
    cout << "  +------------------------------------------------------+\n";
    cout << "  |              SEMESTER GRADE REPORT                  |\n";
    cout << "  |-----------------------------------------------------|\n";
    cout << "  | Course             | Grade | Credits | Grade Points |\n";
    cout << "  |-----------------------------------------------------|\n";

    double totalPoints = 0;
    int totalCredits = 0;

    for (const auto& c : courses) {
        double earned = c.gradePoints * c.creditHours;
        totalPoints += earned;
        totalCredits += c.creditHours;

        cout << "  | " << left << setw(18) << c.name
             << " | " << setw(5) << c.grade
             << " | " << setw(7) << c.creditHours
             << " | " << fixed << setprecision(2) << setw(12) << earned << "|\n";
    }

    cout << "  |-----------------------------------------------------|\n";
    cout << "  | Total Credits        : " << setw(5) << totalCredits << "                 |\n";
    cout << "  | Total Grade Points   : " << fixed << setprecision(2) << setw(6) << totalPoints << "         |\n";
    cout << "  |-----------------------------------------------------|\n";
    cout << "  | CGPA                 : " << fixed << setprecision(2) << cgpa
         << " / 4.00              |\n";
    cout << "  +------------------------------------------------------+\n";
}

int main() {
    cout << "\n  ========================================\n";
    cout << "         CGPA CALCULATOR \n";
    cout << "  ========================================\n\n";

    int numSemesters;
    cout << "  How many semesters do you want to enter? ";
    cin >> numSemesters;

    double overallPoints = 0;
    int overallCredits = 0;

    for (int s = 1; s <= numSemesters; s++) {
        cout << "\n  --- Semester " << s << " ---\n";

        int numCourses;
        cout << "  Number of courses: ";
        cin >> numCourses;
        cin.ignore();

        vector<Course> courses;

        for (int i = 1; i <= numCourses; i++) {
            Course c;

            cout << "\n  Course " << i << " name: ";
            getline(cin, c.name);

            while (true) {
                cout << "  Grade: ";
                cin >> c.grade;
                c.gradePoints = gradeToPoints(c.grade);
                if (c.gradePoints >= 0) break;
                cout << "  Invalid grade.\n";
            }

            while (true) {
                cout << "  Credit hours (1-6): ";
                cin >> c.creditHours;
                if (c.creditHours >= 1 && c.creditHours <= 6) break;
                cout << "  Invalid credit hours.\n";
            }

            cin.ignore();
            courses.push_back(c);
        }

        double semPoints = 0;
        int semCredits = 0;

        for (const auto& c : courses) {
            semPoints += c.gradePoints * c.creditHours;
            semCredits += c.creditHours;
        }

        double semGPA = (semCredits > 0) ? semPoints / semCredits : 0.0;

        overallPoints += semPoints;
        overallCredits += semCredits;

        cout << "\n  Semester " << s << " GPA: " << semGPA << "\n";
        displaySummary(courses, semGPA);
    }

    double cgpa = (overallCredits > 0) ? overallPoints / overallCredits : 0.0;

    cout << "\n  +--------------------------------------+\n";
    cout << "  | OVERALL CGPA : " << cgpa << " / 4.00 |\n";
    cout << "  +--------------------------------------+\n";

    return 0;
}
