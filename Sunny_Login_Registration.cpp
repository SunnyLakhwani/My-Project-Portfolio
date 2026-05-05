#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <algorithm>
#include <limits>
#include <cctype>

using namespace std;

const string DB_FILE = "users.dat";

// ----------------------------------------------
// Simple hash
// ----------------------------------------------
string hashPassword(const string& password) {
    unsigned long hash = 5381;

    for (size_t i = 0; i < password.size(); i++) {
        char c = password[i];
        hash = ((hash << 5) + hash) ^ (unsigned long)c;
    }

    ostringstream oss;
    oss << hex << hash;
    return oss.str();
}

// ----------------------------------------------
// Check username exists
// ----------------------------------------------
bool usernameExists(const string& username) {
    ifstream file(DB_FILE.c_str());
    if (!file.is_open()) return false;

    string line, storedUser;

    while (getline(file, line)) {
        istringstream iss(line);
        getline(iss, storedUser, ':');
        if (storedUser == username) return true;
    }

    return false;
}

// ----------------------------------------------
// Validate username
// ----------------------------------------------
bool validateUsername(const string& username) {
    if (username.length() < 3 || username.length() > 20) return false;

    for (size_t i = 0; i < username.size(); i++) {
        char c = username[i];
        if (!isalnum(c) && c != '_') return false;
    }

    return true;
}

// ----------------------------------------------
// Validate password
// ----------------------------------------------
bool validatePassword(const string& password) {
    if (password.length() < 6) return false;

    bool hasUpper = false, hasDigit = false;

    for (size_t i = 0; i < password.size(); i++) {
        char c = password[i];
        if (isupper(c)) hasUpper = true;
        if (isdigit(c)) hasDigit = true;
    }

    return hasUpper && hasDigit;
}

// ----------------------------------------------
// Password input
// ----------------------------------------------
string readPassword() {
    string password;
    char ch;

    while ((ch = cin.get()) != '\n' && ch != EOF) {
        if (ch == '\b' || ch == 127) {
            if (!password.empty()) {
                password.erase(password.size() - 1);
                cout << "\b \b";
            }
        } else {
            password += ch;
            cout << '*';
        }
    }

    cout << "\n";
    return password;
}

// ----------------------------------------------
// Register user
// ----------------------------------------------
void registerUser() {
    cout << "\n-- New Registration ---------------\n";

    string username;

    while (true) {
        cout << "Username (3-20 chars, letters/digits/_): ";
        cin >> username;
        cin.ignore(numeric_limits<streamsize>::max(), '\n');

        if (!validateUsername(username)) {
            cout << "Invalid username.\n";
            continue;
        }

        if (usernameExists(username)) {
            cout << "Username already exists.\n";
            continue;
        }

        break;
    }

    string password, confirmPass;

    while (true) {
        cout << "Password (min 6 chars, 1 uppercase, 1 digit): ";
        password = readPassword();

        if (!validatePassword(password)) {
            cout << "Weak password.\n";
            continue;
        }

        cout << "Confirm Password: ";
        confirmPass = readPassword();

        if (password != confirmPass) {
            cout << "Passwords do not match.\n";
            continue;
        }

        break;
    }

    ofstream file(DB_FILE.c_str(), ios::app);

    if (!file.is_open()) {
        cout << "Error: Cannot open file.\n";
        return;
    }

    file << username << ":" << hashPassword(password) << "\n";
    file.close();

    cout << "Account created successfully!\n\n";
}

// ----------------------------------------------
// Login user
// ----------------------------------------------
void loginUser() {
    cout << "\n-- Login ---------------\n";

    string username;
    cout << "Username: ";
    cin >> username;
    cin.ignore(numeric_limits<streamsize>::max(), '\n');

    cout << "Password: ";
    string password = readPassword();

    ifstream file(DB_FILE.c_str());
    if (!file.is_open()) {
        cout << "No users found.\n";
        return;
    }

    string line, storedUser, storedHash;
    bool found = false;

    while (getline(file, line)) {
        istringstream iss(line);
        getline(iss, storedUser, ':');
        getline(iss, storedHash);

        if (storedUser == username) {
            found = true;

            if (storedHash == hashPassword(password)) {
                cout << "Login successful!\n\n";
            } else {
                cout << "Wrong password.\n\n";
            }
            break;
        }
    }

    if (!found)
        cout << "User not found.\n\n";
}

// ----------------------------------------------
// Main
// ----------------------------------------------
int main() {
    int choice;
    
    cout << "\n ==========================================\n"; cout << " LOGIN & REGISTRATION \n"; cout << " ==========================================\n";

    while (true) {
        cout << "\n1. Register\n2. Login\n3. Exit\nChoice: ";
        cin >> choice;
        cin.ignore(numeric_limits<streamsize>::max(), '\n');

        if (choice == 1) registerUser();
        else if (choice == 2) loginUser();
        else if (choice == 3) break;
        else cout << "Invalid choice\n";
    }

    return 0;
}
