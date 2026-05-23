"""
Task Automation with Python Scripts — CodeAlpha Internship Task 3
Author: Intern
Description: A unified automation toolkit covering all three required subtasks:
  1. Move all .jpg files from a source folder into a dated subfolder
  2. Extract all email addresses from a .txt file (with deduplication & stats)
  3. Scrape the <title> of a webpage and save it to a file

Run the script and choose which automation to execute from the menu.
"""

import os
import re
import shutil
import urllib.request
import urllib.error
import html
from datetime import datetime


# ── ANSI colors ───────────────────────────────────────────────────────────────
class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    MAGENTA= "\033[95m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

def col(text, *codes):
    return "".join(codes) + str(text) + C.RESET

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def divider(char="─", width=58, color=C.CYAN):
    print(col(char * width, color))

def header(title):
    clear()
    print(col("=" * 58, C.BOLD + C.MAGENTA))
    print(col(f"  🤖  AUTOMATION TOOLKIT  —  {title}", C.BOLD + C.CYAN))
    print(col("=" * 58, C.BOLD + C.MAGENTA))
    print()


# ═══════════════════════════════════════════════════════════
#   AUTOMATION 1 — Move .jpg files to a dated subfolder
# ═══════════════════════════════════════════════════════════
def automate_jpg_mover():
    """
    Scans a source folder recursively for .jpg / .jpeg files and
    moves them into <source_folder>/Sorted_Photos/YYYY-MM-DD/.
    Renames duplicates automatically instead of overwriting.
    Prints a full report with file sizes.
    """
    header("JPG File Organiser")
    print(col("  This automation moves all .jpg/.jpeg files from a\n"
              "  source folder into a dated 'Sorted_Photos' subfolder.\n", C.DIM))

    # ── Get source folder ─────────────────────────────────────────────────────
    src = input(col("  Source folder path (Enter = current directory): ", C.CYAN)).strip()
    if not src:
        src = os.getcwd()
    src = os.path.abspath(src)

    if not os.path.isdir(src):
        print(col(f"\n  ❌  Directory not found: {src}", C.RED))
        return

    # ── Create destination folder ─────────────────────────────────────────────
    today     = datetime.now().strftime("%Y-%m-%d")
    dest_dir  = os.path.join(src, "Sorted_Photos", today)
    os.makedirs(dest_dir, exist_ok=True)

    # ── Collect .jpg files (walk recursively, skip dest_dir itself) ───────────
    jpg_files = []
    for root, dirs, files in os.walk(src):
        # Avoid recursing into the destination folder
        dirs[:] = [d for d in dirs if os.path.join(root, d) != dest_dir
                   and d != "Sorted_Photos"]
        for fname in files:
            if fname.lower().endswith((".jpg", ".jpeg")):
                jpg_files.append(os.path.join(root, fname))

    if not jpg_files:
        print(col(f"\n  ℹ️   No .jpg/.jpeg files found in: {src}", C.YELLOW))
        return

    print(col(f"\n  Found {len(jpg_files)} file(s). Moving...\n", C.YELLOW))
    divider()

    moved   = 0
    skipped = 0
    total_bytes = 0

    for src_path in jpg_files:
        fname    = os.path.basename(src_path)
        dest_path = os.path.join(dest_dir, fname)

        # Rename if a file with that name already exists in dest
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(fname)
            counter   = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
                counter  += 1
            new_name = os.path.basename(dest_path)
            rename_note = col(f" → renamed to {new_name}", C.YELLOW)
        else:
            rename_note = ""

        try:
            size = os.path.getsize(src_path)
            shutil.move(src_path, dest_path)
            total_bytes += size
            moved += 1
            size_str = f"{size / 1024:.1f} KB" if size < 1_048_576 else f"{size / 1_048_576:.2f} MB"
            print(f"  {col('✅', C.GREEN)}  {fname:<35} {col(size_str, C.DIM)}{rename_note}")
        except Exception as e:
            skipped += 1
            print(f"  {col('❌', C.RED)}  {fname}  — {e}")

    divider()
    mb = total_bytes / 1_048_576
    print(col(f"\n  Done!  {moved} moved  |  {skipped} skipped  |  {mb:.2f} MB total", C.GREEN + C.BOLD))
    print(col(f"  Destination: {dest_dir}", C.DIM))

    # ── Write a log file ──────────────────────────────────────────────────────
    log_path = os.path.join(dest_dir, "_move_log.txt")
    with open(log_path, "w") as log:
        log.write(f"JPG Organiser — Run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Source      : {src}\n")
        log.write(f"Destination : {dest_dir}\n")
        log.write(f"Files moved : {moved}\n")
        log.write(f"Files skipped: {skipped}\n")
        log.write(f"Total size  : {mb:.2f} MB\n\n")
        for p in jpg_files:
            log.write(f"  {p}\n")
    print(col(f"  Log saved → {log_path}\n", C.DIM))


# ═══════════════════════════════════════════════════════════
#   AUTOMATION 2 — Extract emails from a .txt file
# ═══════════════════════════════════════════════════════════
# Robust RFC-5322-ish email regex
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

def automate_email_extractor():
    """
    Reads a .txt file, extracts every unique email address,
    shows domain-level statistics, and saves results to a
    separate .txt file with a timestamp.
    """
    header("Email Address Extractor")
    print(col("  Extracts all unique email addresses from a .txt file,\n"
              "  deduplicates them, and saves results with statistics.\n", C.DIM))

    # ── Get input file ────────────────────────────────────────────────────────
    src_file = input(col("  Path to source .txt file: ", C.CYAN)).strip()
    if not src_file:
        print(col("\n  ❌  No file specified.", C.RED))
        return
    if not os.path.isfile(src_file):
        print(col(f"\n  ❌  File not found: {src_file}", C.RED))
        return

    # ── Read & extract ────────────────────────────────────────────────────────
    with open(src_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    all_found = EMAIL_REGEX.findall(content)
    # Normalise to lowercase, deduplicate while preserving order
    seen   = set()
    unique = []
    for email in all_found:
        norm = email.lower()
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)

    print()
    divider()
    if not unique:
        print(col("  ℹ️   No email addresses found in the file.", C.YELLOW))
        return

    print(col(f"  Found {len(all_found)} total  |  {len(unique)} unique\n", C.YELLOW))

    # ── Domain statistics ─────────────────────────────────────────────────────
    domain_count: dict = {}
    for email in unique:
        domain = email.split("@")[1]
        domain_count[domain] = domain_count.get(domain, 0) + 1

    top_domains = sorted(domain_count.items(), key=lambda x: x[1], reverse=True)[:5]
    print(col("  Top Domains:", C.BOLD))
    for domain, count in top_domains:
        bar = col("█" * count, C.CYAN) + col("░" * (10 - min(count, 10)), C.DIM)
        print(f"    {domain:<30} {bar}  {count}")

    print()
    print(col("  Extracted Emails:", C.BOLD))
    divider()
    for i, email in enumerate(unique, 1):
        print(f"  {col(str(i).rjust(3), C.DIM)}  {col(email, C.GREEN)}")
    divider()

    # ── Save output ───────────────────────────────────────────────────────────
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file   = f"extracted_emails_{timestamp}.txt"
    with open(out_file, "w") as f:
        f.write(f"Email Extraction Report\n")
        f.write(f"Source file : {src_file}\n")
        f.write(f"Generated   : {datetime.now().strftime('%d %B %Y  %H:%M:%S')}\n")
        f.write(f"Total found : {len(all_found)}\n")
        f.write(f"Unique      : {len(unique)}\n")
        f.write("\n── Domain Breakdown ──\n")
        for domain, count in sorted(domain_count.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {domain}: {count}\n")
        f.write("\n── Email Addresses ──\n")
        for email in unique:
            f.write(email + "\n")

    print(col(f"\n  ✅  Results saved → {out_file}\n", C.GREEN))


# ═══════════════════════════════════════════════════════════
#   AUTOMATION 3 — Scrape webpage title and save it
# ═══════════════════════════════════════════════════════════
def fetch_page_title(url: str) -> str | None:
    """
    Fetches a webpage using urllib (no external libraries needed)
    and extracts the <title> tag content.
    Returns the title string or None on failure.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read(200_000)          # read up to 200 KB
            encoding = resp.headers.get_content_charset("utf-8")
            text = raw.decode(encoding, errors="replace")
    except urllib.error.URLError as e:
        raise ConnectionError(str(e))

    # Regex to find <title>...</title>
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = match.group(1).strip()
    # Decode HTML entities (e.g. &amp; → &)
    title = html.unescape(title)
    # Collapse whitespace
    title = re.sub(r"\s+", " ", title)
    return title


def automate_title_scraper():
    """
    Scrapes the <title> of one or more URLs and saves a report.
    """
    header("Webpage Title Scraper")
    print(col("  Enter URLs one per line. Leave blank and press Enter\n"
              "  when done to start scraping.\n", C.DIM))

    urls = []
    while True:
        url = input(col(f"  URL {len(urls)+1} (or Enter to finish): ", C.CYAN)).strip()
        if not url:
            break
        urls.append(url)

    if not urls:
        print(col("\n  No URLs entered.", C.YELLOW))
        return

    print()
    divider()

    results = []
    for url in urls:
        print(col(f"  Fetching: {url}", C.DIM), end="", flush=True)
        try:
            title = fetch_page_title(url)
            if title:
                print(f"\r  {col('✅', C.GREEN)} {col(url, C.CYAN)}")
                print(f"     Title: {col(title, C.YELLOW)}")
                results.append({"url": url, "status": "OK", "title": title})
            else:
                print(f"\r  {col('⚠️ ', C.YELLOW)} {url}")
                print(f"     {col('No <title> tag found', C.YELLOW)}")
                results.append({"url": url, "status": "NO_TITLE", "title": ""})
        except ConnectionError as e:
            print(f"\r  {col('❌', C.RED)} {url}")
            print(f"     {col(str(e), C.RED)}")
            results.append({"url": url, "status": "ERROR", "title": str(e)})
        print()

    divider()

    # ── Save report ───────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file  = f"scraped_titles_{timestamp}.txt"

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("Webpage Title Scrape Report\n")
        f.write(f"Generated : {datetime.now().strftime('%d %B %Y  %H:%M:%S')}\n")
        f.write(f"URLs      : {len(urls)}\n")
        f.write("─" * 60 + "\n\n")
        for r in results:
            f.write(f"URL    : {r['url']}\n")
            f.write(f"Status : {r['status']}\n")
            f.write(f"Title  : {r['title']}\n")
            f.write("\n")

    ok_count = sum(1 for r in results if r["status"] == "OK")
    print(col(f"  ✅  {ok_count}/{len(urls)} titles scraped successfully.", C.GREEN + C.BOLD))
    print(col(f"  Report saved → {out_file}\n", C.DIM))


# ═══════════════════════════════════════════════════════════
#   MAIN MENU
# ═══════════════════════════════════════════════════════════
def main():
    while True:
        header("MAIN MENU")
        print(f"  {col('1', C.GREEN)}  🗂️   Move .jpg Files to Sorted Folder")
        print(f"  {col('2', C.CYAN)}  📧  Extract Emails from .txt File")
        print(f"  {col('3', C.YELLOW)}  🌐  Scrape Webpage Title(s)")
        print(f"  {col('4', C.RED)}  🚪  Exit")
        print()

        choice = input(col("  Select automation (1–4): ", C.CYAN)).strip()

        if choice == "1":
            automate_jpg_mover()
            input(col("\n  Press Enter to return to menu...", C.DIM))
        elif choice == "2":
            automate_email_extractor()
            input(col("\n  Press Enter to return to menu...", C.DIM))
        elif choice == "3":
            automate_title_scraper()
            input(col("\n  Press Enter to return to menu...", C.DIM))
        elif choice == "4":
            print(col("\n  Automation suite closed. Goodbye!\n", C.CYAN))
            break
        else:
            print(col("  Invalid option. Enter 1, 2, 3, or 4.\n", C.RED))
            import time; time.sleep(1)


if __name__ == "__main__":
    main()