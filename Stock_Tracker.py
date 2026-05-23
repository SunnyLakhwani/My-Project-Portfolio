import os
import csv
import time
import random
from datetime import datetime


# ── ANSI colors ───────────────────────────────────────────────────────────────
class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    MAGENTA= "\033[95m"
    BLUE   = "\033[94m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

def col(text, *codes):
    return "".join(codes) + str(text) + C.RESET

def clear():
    os.system("cls" if os.name == "nt" else "clear")


# ── Hardcoded stock price data (price, simulated daily change %) ──────────────
STOCK_DATA = {
    "AAPL":  {"name": "Apple Inc.",            "price": 189.30, "change": +1.24},
    "TSLA":  {"name": "Tesla Inc.",            "price": 248.50, "change": -2.87},
    "GOOGL": {"name": "Alphabet Inc.",         "price": 174.10, "change": +0.65},
    "MSFT":  {"name": "Microsoft Corp.",       "price": 415.80, "change": +1.05},
    "AMZN":  {"name": "Amazon.com Inc.",       "price": 198.40, "change": -0.43},
    "NVDA":  {"name": "NVIDIA Corp.",          "price": 875.00, "change": +3.12},
    "META":  {"name": "Meta Platforms Inc.",   "price": 520.60, "change": +0.88},
    "NFLX":  {"name": "Netflix Inc.",          "price": 680.20, "change": -1.55},
    "BABA":  {"name": "Alibaba Group",         "price": 79.40,  "change": -0.22},
    "PYPL":  {"name": "PayPal Holdings",       "price": 64.90,  "change": +2.10},
}

# portfolio: {ticker: {"qty": int, "avg_buy_price": float}}
portfolio = {}


# ── Helpers ───────────────────────────────────────────────────────────────────
def current_price(ticker):
    """Return the current (hardcoded) price."""
    return STOCK_DATA[ticker]["price"]

def change_pct(ticker):
    return STOCK_DATA[ticker]["change"]

def fmt_money(val):
    return f"${val:,.2f}"

def fmt_pct(val):
    sign = "+" if val >= 0 else ""
    color = C.GREEN if val >= 0 else C.RED
    return col(f"{sign}{val:.2f}%", color)

def divider(char="─", width=60, color=C.CYAN):
    print(col(char * width, color))


# ── Header ────────────────────────────────────────────────────────────────────
def print_header():
    clear()
    print(col("=" * 60, C.BOLD + C.BLUE))
    print(col("   📈  STOCK PORTFOLIO TRACKER  |  Sunny Lakhwani", C.BOLD + C.CYAN))
    print(col(f"   {datetime.now().strftime('%A, %d %B %Y  %H:%M:%S')}", C.DIM))
    print(col("=" * 60, C.BOLD + C.BLUE))
    print()


# ── Show available stocks ─────────────────────────────────────────────────────
def show_market():
    print_header()
    print(col("  AVAILABLE STOCKS (Today's Prices)\n", C.BOLD + C.YELLOW))
    header = f"  {'Ticker':<8} {'Company':<26} {'Price':>10}  {'Change':>8}"
    print(col(header, C.BOLD))
    divider()
    for ticker, info in STOCK_DATA.items():
        price_str  = col(fmt_money(info["price"]), C.CYAN)
        change_str = fmt_pct(info["change"])
        print(f"  {col(ticker, C.BOLD):<18} {info['name']:<26} {price_str:>18}  {change_str}")
    divider()
    print()


# ── Add stock to portfolio ────────────────────────────────────────────────────
def add_stock():
    show_market()
    print(col("  ── ADD STOCK ──\n", C.BOLD + C.GREEN))
    ticker = input(col("  Enter ticker symbol (e.g. AAPL): ", C.CYAN)).strip().upper()

    if ticker not in STOCK_DATA:
        print(col(f"\n  ❌  '{ticker}' is not in our stock list.", C.RED))
        time.sleep(1.5)
        return

    try:
        qty = int(input(col("  Quantity to buy: ", C.CYAN)).strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        print(col("\n  ❌  Invalid quantity.", C.RED))
        time.sleep(1.5)
        return

    try:
        buy_price_input = input(
            col(f"  Buy price per share (press Enter to use current ${current_price(ticker):.2f}): ", C.CYAN)
        ).strip()
        buy_price = float(buy_price_input) if buy_price_input else current_price(ticker)
        if buy_price <= 0:
            raise ValueError
    except ValueError:
        print(col("\n  ❌  Invalid price.", C.RED))
        time.sleep(1.5)
        return

    if ticker in portfolio:
        # Weighted average for existing holding
        old_qty   = portfolio[ticker]["qty"]
        old_avg   = portfolio[ticker]["avg_buy_price"]
        new_qty   = old_qty + qty
        new_avg   = ((old_qty * old_avg) + (qty * buy_price)) / new_qty
        portfolio[ticker] = {"qty": new_qty, "avg_buy_price": round(new_avg, 4)}
        print(col(f"\n  ✅  Updated {ticker}: now holding {new_qty} shares @ avg {fmt_money(new_avg)}", C.GREEN))
    else:
        portfolio[ticker] = {"qty": qty, "avg_buy_price": buy_price}
        print(col(f"\n  ✅  Added {qty} shares of {ticker} @ {fmt_money(buy_price)}", C.GREEN))

    time.sleep(1.8)


# ── Remove stock ──────────────────────────────────────────────────────────────
def remove_stock():
    if not portfolio:
        print(col("\n  Your portfolio is empty.\n", C.YELLOW))
        time.sleep(1.5)
        return

    print_header()
    print(col("  ── REMOVE / SELL STOCK ──\n", C.BOLD + C.RED))
    print("  Current holdings:", ", ".join(col(t, C.CYAN) for t in portfolio))
    ticker = input(col("\n  Enter ticker to sell: ", C.CYAN)).strip().upper()

    if ticker not in portfolio:
        print(col(f"\n  ❌  You don't own '{ticker}'.", C.RED))
        time.sleep(1.5)
        return

    owned = portfolio[ticker]["qty"]
    try:
        qty = int(input(col(f"  Shares to sell (you own {owned}): ", C.CYAN)).strip())
        if qty <= 0 or qty > owned:
            raise ValueError
    except ValueError:
        print(col("\n  ❌  Invalid quantity.", C.RED))
        time.sleep(1.5)
        return

    if qty == owned:
        del portfolio[ticker]
        print(col(f"\n  ✅  Sold all {owned} shares of {ticker}.", C.GREEN))
    else:
        portfolio[ticker]["qty"] -= qty
        print(col(f"\n  ✅  Sold {qty} shares. {portfolio[ticker]['qty']} remaining.", C.GREEN))

    time.sleep(1.8)


# ── Portfolio summary ─────────────────────────────────────────────────────────
def view_portfolio():
    print_header()
    print(col("  ── PORTFOLIO SUMMARY ──\n", C.BOLD + C.MAGENTA))

    if not portfolio:
        print(col("  Your portfolio is empty. Start by adding stocks!\n", C.YELLOW))
        input(col("  Press Enter to continue...", C.DIM))
        return

    total_invested = 0.0
    total_current  = 0.0

    col_h = f"  {'Ticker':<8} {'Qty':>5}  {'Avg Buy':>10}  {'Cur Price':>10}  {'Invested':>12}  {'Value':>12}  {'P/L':>10}"
    print(col(col_h, C.BOLD))
    divider()

    for ticker, holding in portfolio.items():
        qty        = holding["qty"]
        avg_buy    = holding["avg_buy_price"]
        cur        = current_price(ticker)
        invested   = qty * avg_buy
        value      = qty * cur
        pl         = value - invested
        pl_pct     = ((cur - avg_buy) / avg_buy) * 100

        total_invested += invested
        total_current  += value

        pl_color = C.GREEN if pl >= 0 else C.RED
        pl_str   = col(f"{'+'if pl>=0 else ''}{fmt_money(pl)}", pl_color)

        print(
            f"  {col(ticker, C.BOLD):<16} {qty:>5}  {fmt_money(avg_buy):>10}  "
            f"{col(fmt_money(cur), C.CYAN):>18}  {fmt_money(invested):>12}  "
            f"{fmt_money(value):>12}  {pl_str}"
        )

    divider()

    total_pl      = total_current - total_invested
    total_pl_pct  = ((total_current - total_invested) / total_invested * 100) if total_invested else 0
    total_color   = C.GREEN if total_pl >= 0 else C.RED

    print()
    print(f"  {col('Total Invested :', C.BOLD)}  {col(fmt_money(total_invested), C.YELLOW)}")
    print(f"  {col('Total Value     :', C.BOLD)}  {col(fmt_money(total_current), C.CYAN)}")
    print(f"  {col('Overall P/L     :', C.BOLD)}  {col(fmt_money(total_pl), total_color)}  ({fmt_pct(total_pl_pct)})")
    print()

    # ── ASCII bar chart of holdings by value ──────────────────────────────────
    print(col("  ── Holdings by Value ──\n", C.BOLD + C.YELLOW))
    max_value = max(portfolio[t]["qty"] * current_price(t) for t in portfolio)
    bar_width = 35
    for ticker in portfolio:
        val    = portfolio[ticker]["qty"] * current_price(ticker)
        filled = int((val / max_value) * bar_width)
        bar    = col("█" * filled, C.CYAN) + col("░" * (bar_width - filled), C.DIM)
        print(f"  {col(ticker, C.BOLD):<14} {bar}  {col(fmt_money(val), C.YELLOW)}")
    print()

    input(col("  Press Enter to continue...", C.DIM))


# ── Export portfolio ──────────────────────────────────────────────────────────
def export_portfolio():
    if not portfolio:
        print(col("\n  Nothing to export — portfolio is empty.\n", C.YELLOW))
        time.sleep(1.5)
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_file  = f"portfolio_{timestamp}.txt"
    csv_file  = f"portfolio_{timestamp}.csv"

    rows = []
    total_invested = 0.0
    total_value    = 0.0

    for ticker, h in portfolio.items():
        qty      = h["qty"]
        avg_buy  = h["avg_buy_price"]
        cur      = current_price(ticker)
        invested = qty * avg_buy
        value    = qty * cur
        pl       = value - invested
        pl_pct   = ((cur - avg_buy) / avg_buy) * 100
        total_invested += invested
        total_value    += value
        rows.append({
            "Ticker": ticker,
            "Company": STOCK_DATA[ticker]["name"],
            "Quantity": qty,
            "Avg Buy Price": round(avg_buy, 2),
            "Current Price": round(cur, 2),
            "Invested ($)": round(invested, 2),
            "Current Value ($)": round(value, 2),
            "Profit/Loss ($)": round(pl, 2),
            "P/L (%)": round(pl_pct, 2),
        })

    # ── Write .txt ──
    with open(txt_file, "w") as f:
        f.write("=" * 65 + "\n")
        f.write("  STOCK PORTFOLIO REPORT\n")
        f.write(f"  Generated: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n")
        f.write("=" * 65 + "\n\n")
        for r in rows:
            f.write(f"  {r['Ticker']} — {r['Company']}\n")
            f.write(f"    Qty          : {r['Quantity']}\n")
            f.write(f"    Avg Buy Price: ${r['Avg Buy Price']}\n")
            f.write(f"    Current Price: ${r['Current Price']}\n")
            f.write(f"    Invested     : ${r['Invested ($)']}\n")
            f.write(f"    Current Value: ${r['Current Value ($)']}\n")
            f.write(f"    P/L          : ${r['Profit/Loss ($)']}  ({r['P/L (%)']}%)\n")
            f.write("\n")
        f.write("-" * 65 + "\n")
        f.write(f"  Total Invested  : ${total_invested:,.2f}\n")
        f.write(f"  Total Value     : ${total_value:,.2f}\n")
        total_pl = total_value - total_invested
        f.write(f"  Overall P/L     : ${total_pl:,.2f}\n")
        f.write("=" * 65 + "\n")

    # ── Write .csv ──
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(col(f"\n  ✅  Exported:\n    📄 {txt_file}\n    📊 {csv_file}\n", C.GREEN))
    time.sleep(2.5)


# ── Main menu ─────────────────────────────────────────────────────────────────
def main():
    while True:
        print_header()
        print(col("  MAIN MENU\n", C.BOLD + C.YELLOW))
        print(f"  {col('1', C.GREEN)}  View Market Prices")
        print(f"  {col('2', C.GREEN)}  Add Stock to Portfolio")
        print(f"  {col('3', C.GREEN)}  Sell / Remove Stock")
        print(f"  {col('4', C.CYAN)}  View Portfolio Summary")
        print(f"  {col('5', C.MAGENTA)}  Export Portfolio (.txt + .csv)")
        print(f"  {col('6', C.RED)}  Quit")
        print()

        choice = input(col("  Select option: ", C.CYAN)).strip()

        if choice == "1":
            show_market()
            input(col("  Press Enter to continue...", C.DIM))
        elif choice == "2":
            add_stock()
        elif choice == "3":
            remove_stock()
        elif choice == "4":
            view_portfolio()
        elif choice == "5":
            export_portfolio()
        elif choice == "6":
            print(col("\n  Goodbye! Happy investing! 📈\n", C.CYAN))
            break
        else:
            print(col("  Invalid option. Please enter 1–6.", C.RED))
            time.sleep(1)


if __name__ == "__main__":
    main()