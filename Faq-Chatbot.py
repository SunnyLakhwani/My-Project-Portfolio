
import tkinter as tk
from tkinter import scrolledtext
import nltk
import string
import threading
import time
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Download required NLTK data
nltk.download("punkt", quiet=True)
nltk.download("stopwords", quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("punkt_tab", quiet=True)

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer


# ─────────────────────────────────────────────
#  FAQ Database (Python / Programming Topic)
# ─────────────────────────────────────────────
FAQ_DATA = [
    {
        "question": "What is Python?",
        "answer": "Python is a high-level, interpreted, general-purpose programming language known for its clear syntax and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming."
    },
    {
        "question": "How do I install Python?",
        "answer": "You can install Python from the official website python.org. Download the installer for your OS (Windows/Mac/Linux), run it, and make sure to check 'Add Python to PATH' during installation."
    },
    {
        "question": "What are Python data types?",
        "answer": "Python has several built-in data types: int (integers), float (decimal numbers), str (strings/text), bool (True/False), list (ordered mutable collection), tuple (ordered immutable collection), dict (key-value pairs), and set (unordered unique elements)."
    },
    {
        "question": "What is a list in Python?",
        "answer": "A list is an ordered, mutable collection in Python that can hold elements of different types. Lists are defined using square brackets, e.g., my_list = [1, 'hello', 3.14]. You can add, remove, or change elements."
    },
    {
        "question": "What is a dictionary in Python?",
        "answer": "A dictionary (dict) stores data as key-value pairs. It is defined using curly braces, e.g., person = {'name': 'Ali', 'age': 25}. You access values by their key: person['name'] returns 'Ali'."
    },
    {
        "question": "What are functions in Python?",
        "answer": "Functions are reusable blocks of code defined using the 'def' keyword. Example: def greet(name): return f'Hello, {name}'. They help organize code and avoid repetition."
    },
    {
        "question": "What is a class in Python?",
        "answer": "A class is a blueprint for creating objects in object-oriented programming. It defines attributes (data) and methods (functions). Example: class Car: def __init__(self, brand): self.brand = brand"
    },
    {
        "question": "What is machine learning?",
        "answer": "Machine Learning (ML) is a subset of AI that enables computers to learn from data without being explicitly programmed. It uses algorithms to find patterns and make predictions or decisions automatically."
    },
    {
        "question": "What is artificial intelligence?",
        "answer": "Artificial Intelligence (AI) is the simulation of human intelligence in machines. It includes areas like machine learning, natural language processing, computer vision, and robotics."
    },
    {
        "question": "What is deep learning?",
        "answer": "Deep learning is a subset of machine learning that uses neural networks with many layers (deep networks) to automatically learn complex patterns from large amounts of data. It powers image recognition, speech synthesis, and language models."
    },
    {
        "question": "What is NumPy?",
        "answer": "NumPy is a Python library for numerical computing. It provides support for large multi-dimensional arrays and matrices, along with mathematical functions. Install it with: pip install numpy"
    },
    {
        "question": "What is Pandas?",
        "answer": "Pandas is a Python data analysis library that provides DataFrames and Series for structured data manipulation. It makes reading, cleaning, and analyzing CSV/Excel files easy. Install with: pip install pandas"
    },
    {
        "question": "What is pip?",
        "answer": "pip is Python's package installer. It lets you install third-party libraries from PyPI (Python Package Index). Example usage: pip install requests"
    },
    {
        "question": "What is a virtual environment?",
        "answer": "A virtual environment is an isolated Python environment for a project. It keeps dependencies separate from other projects. Create one with: python -m venv myenv, then activate it."
    },
    {
        "question": "What is exception handling in Python?",
        "answer": "Exception handling lets you catch and handle runtime errors gracefully using try-except blocks. Example: try: x = 1/0 except ZeroDivisionError: print('Cannot divide by zero!')"
    },
    {
        "question": "What is a for loop?",
        "answer": "A for loop iterates over a sequence (list, string, range, etc.). Example: for i in range(5): print(i) — this prints numbers 0 through 4."
    },
    {
        "question": "What is the difference between a list and a tuple?",
        "answer": "Both store ordered collections of items. The key difference: lists are mutable (can be changed), while tuples are immutable (cannot be changed after creation). Tuples use parentheses (), lists use square brackets []."
    },
    {
        "question": "What is recursion?",
        "answer": "Recursion is when a function calls itself to solve a smaller version of the same problem. Example: def factorial(n): return 1 if n == 0 else n * factorial(n-1). Always include a base case to stop recursion."
    },
    {
        "question": "What is Git?",
        "answer": "Git is a distributed version control system used to track changes in source code. It lets multiple developers collaborate. Common commands: git init, git add, git commit, git push, git pull."
    },
    {
        "question": "What is GitHub?",
        "answer": "GitHub is a cloud-based platform for hosting Git repositories. It enables collaboration, code review, issue tracking, and project management. You can upload your projects and share them publicly."
    },
    {
        "question": "How do I read a file in Python?",
        "answer": "Use the open() function: with open('file.txt', 'r') as f: content = f.read(). The 'with' statement ensures the file is properly closed after reading."
    },
    {
        "question": "What are lambda functions?",
        "answer": "Lambda functions are anonymous (unnamed) functions defined using the 'lambda' keyword. Example: square = lambda x: x ** 2. They are useful for short, one-liner operations."
    },
    {
        "question": "What is NLP?",
        "answer": "Natural Language Processing (NLP) is a branch of AI that enables computers to understand, interpret, and generate human language. Applications include chatbots, sentiment analysis, translation, and speech recognition."
    },
    {
        "question": "What is cosine similarity?",
        "answer": "Cosine similarity measures the angle between two vectors in a multi-dimensional space. In NLP, it compares how similar two text documents are regardless of their size. A score of 1 means identical, 0 means no similarity."
    },
    {
        "question": "How to say hello in python?",
        "answer": "In Python, you can print 'Hello, World!' using: print('Hello, World!'). This is traditionally the first program beginners write when learning a new language."
    },
]

# ─────────────────────────────────────────────
#  NLP Preprocessing
# ─────────────────────────────────────────────
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words("english"))


def preprocess(text: str) -> str:
    """Tokenize, lowercase, remove punctuation, stopwords, and lemmatize."""
    tokens = nltk.word_tokenize(text.lower())
    tokens = [t for t in tokens if t not in string.punctuation]
    tokens = [t for t in tokens if t not in stop_words]
    tokens = [lemmatizer.lemmatize(t) for t in tokens]
    return " ".join(tokens)


# Preprocess all FAQ questions once
faq_questions_clean = [preprocess(faq["question"]) for faq in FAQ_DATA]
faq_answers = [faq["answer"] for faq in FAQ_DATA]
faq_questions_raw = [faq["question"] for faq in FAQ_DATA]

# TF-IDF Vectorizer fitted on FAQ questions
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(faq_questions_clean)


# ─────────────────────────────────────────────
#  Matching Engine
# ─────────────────────────────────────────────
GREETINGS = {"hi", "hello", "hey", "hii", "salam", "howdy", "sup"}
GOODBYES  = {"bye", "goodbye", "exit", "quit", "thanks", "thank you"}

def get_response(user_input: str) -> str:
    lower = user_input.strip().lower()

    if lower in GREETINGS:
        return random.choice([
            "Hello! 👋 I'm Sunny Lakhwani's FAQ Bot. Ask me anything about Python or AI!",
            "Hi there! How can I help you today?",
            "Hey! Ready to answer your coding questions! 🚀"
        ])

    if lower in GOODBYES:
        return "Goodbye! Happy coding! 🎉"

    # Preprocess user query
    clean_input = preprocess(user_input)
    if not clean_input.strip():
        return "Could you please rephrase your question? I didn't catch that."

    # Vectorize and compute cosine similarity
    user_vec = vectorizer.transform([clean_input])
    similarities = cosine_similarity(user_vec, tfidf_matrix).flatten()
    best_idx = similarities.argmax()
    best_score = similarities[best_idx]

    THRESHOLD = 0.15  # Minimum similarity to return an answer

    if best_score < THRESHOLD:
        return (
            "I'm not sure about that. Try asking about Python, AI, ML, "
            "Git, or general programming concepts!"
        )

    matched_q = faq_questions_raw[best_idx]
    answer = faq_answers[best_idx]
    confidence = int(best_score * 100)

    return f"**Matched:** {matched_q}\n\n{answer}\n\n[Confidence: {confidence}%]"


# ─────────────────────────────────────────────
#  Chat UI
# ─────────────────────────────────────────────
class ChatbotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 FAQ Chatbot ")
        self.root.geometry("680x600")
        self.root.configure(bg="#0d1117")
        self.root.resizable(True, True)
        self._build_ui()
        self._post_bot("Hello! 👋 I'm Sunny Lakhwani's FAQ Bot. Ask me anything about Python, AI, or programming!")

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#161b22", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="🤖  FAQ Chatbot", font=("Helvetica", 18, "bold"),
                 bg="#161b22", fg="#58a6ff").pack()
        tk.Label(header, text="Made by Sunny Lakhwani | Topic: Python & AI",
                 font=("Helvetica", 9), bg="#161b22", fg="#8b949e").pack()

        # Chat display area
        self.chat_area = scrolledtext.ScrolledText(
            self.root, wrap="word", state="disabled",
            font=("Helvetica", 11), bg="#0d1117", fg="#c9d1d9",
            relief="flat", padx=14, pady=14,
            insertbackground="white"
        )
        self.chat_area.pack(fill="both", expand=True, padx=16, pady=(10, 0))

        # Configure text tags
        self.chat_area.tag_config("user",  foreground="#58a6ff", font=("Helvetica", 11, "bold"))
        self.chat_area.tag_config("bot",   foreground="#3fb950", font=("Helvetica", 11))
        self.chat_area.tag_config("meta",  foreground="#8b949e", font=("Helvetica", 9, "italic"))
        self.chat_area.tag_config("thinking", foreground="#d29922", font=("Helvetica", 11, "italic"))

        # Suggestion chips
        chips_frame = tk.Frame(self.root, bg="#0d1117", pady=6)
        chips_frame.pack(fill="x", padx=16)
        suggestions = ["What is Python?", "What is AI?", "What is Git?", "Show data types"]
        for s in suggestions:
            tk.Button(chips_frame, text=s, font=("Helvetica", 9),
                      bg="#21262d", fg="#8b949e", relief="flat",
                      cursor="hand2", padx=8, pady=4,
                      command=lambda q=s: self._send_message(q)
                      ).pack(side="left", padx=4)

        # Input row
        input_frame = tk.Frame(self.root, bg="#161b22", pady=10)
        input_frame.pack(fill="x", padx=16, pady=(0, 10))

        self.input_var = tk.StringVar()
        self.entry = tk.Entry(input_frame, textvariable=self.input_var,
                              font=("Helvetica", 12), bg="#21262d", fg="#c9d1d9",
                              insertbackground="white", relief="flat",
                              highlightthickness=1, highlightbackground="#30363d",
                              highlightcolor="#58a6ff")
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self._send_message())
        self.entry.focus()

        send_btn = tk.Button(input_frame, text="Send ▶", font=("Helvetica", 11, "bold"),
                             bg="#238636", fg="white", relief="flat",
                             padx=14, pady=8, cursor="hand2",
                             command=self._send_message)
        send_btn.pack(side="right")

        clear_btn = tk.Button(input_frame, text="Clear", font=("Helvetica", 10),
                              bg="#21262d", fg="#8b949e", relief="flat",
                              padx=10, pady=8, cursor="hand2",
                              command=self._clear_chat)
        clear_btn.pack(side="right", padx=(0, 6))

    def _send_message(self, text=None):
        msg = text or self.input_var.get().strip()
        if not msg:
            return
        self.input_var.set("")
        self._post_user(msg)
        threading.Thread(target=self._get_bot_reply, args=(msg,), daemon=True).start()

    def _get_bot_reply(self, user_msg):
        self.root.after(0, self._show_thinking)
        time.sleep(0.6)  # Simulate typing delay
        response = get_response(user_msg)
        self.root.after(0, self._remove_thinking)
        self.root.after(0, self._post_bot, response)

    def _post_user(self, msg):
        self.chat_area.config(state="normal")
        self.chat_area.insert("end", f"\nYou:  ", "user")
        self.chat_area.insert("end", f"{msg}\n", "")
        self.chat_area.config(state="disabled")
        self.chat_area.see("end")

    def _show_thinking(self):
        self.chat_area.config(state="normal")
        self.chat_area.insert("end", "\nBot:  thinking…\n", "thinking")
        self.chat_area.config(state="disabled")
        self.chat_area.see("end")

    def _remove_thinking(self):
        self.chat_area.config(state="normal")
        content = self.chat_area.get("1.0", "end")
        last_thinking = content.rfind("\nBot:  thinking…\n")
        if last_thinking >= 0:
            idx = f"1.0 + {last_thinking} chars"
            end_idx = f"1.0 + {last_thinking + len(chr(10) + 'Bot:  thinking…' + chr(10))} chars"
            self.chat_area.delete(idx, end_idx)
        self.chat_area.config(state="disabled")

    def _post_bot(self, msg):
        self.chat_area.config(state="normal")
        self.chat_area.insert("end", f"\nBot:  ", "user")
        self.chat_area.insert("end", f"{msg}\n", "bot")
        self.chat_area.config(state="disabled")
        self.chat_area.see("end")

    def _clear_chat(self):
        self.chat_area.config(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.config(state="disabled")
        self._post_bot("Chat cleared! Ask me anything about Python or AI 🤖")


# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = ChatbotApp(root)
    root.mainloop()