import socket
import struct
import textwrap
import datetime
import sys
import os

# ── terminal colours ──────────────────────────────────────────────────────────
class C:
    HEADER  = "\033[95m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RESET   = "\033[0m"

# ── helpers ───────────────────────────────────────────────────────────────────
def mac_fmt(raw: bytes) -> str:
    """Convert 6 raw bytes into a colon-separated MAC address string."""
    return ":".join(f"{b:02x}" for b in raw)


def ipv4_fmt(raw: bytes) -> str:
    """Convert 4 raw bytes into a dotted-decimal IPv4 string."""
    return ".".join(map(str, raw))


def indent(text: str, spaces: int = 4) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines())


def timestamp() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


# ── protocol parsers ──────────────────────────────────────────────────────────
def parse_ethernet(raw: bytes):
    """
    Ethernet II frame layout (14 bytes):
      6 dst MAC | 6 src MAC | 2 EtherType
    """
    dst_mac, src_mac, proto = struct.unpack("!6s6sH", raw[:14])
    return mac_fmt(dst_mac), mac_fmt(src_mac), proto, raw[14:]


def parse_ipv4(raw: bytes):
    """
    IPv4 header (minimum 20 bytes):
      version/ihl | dscp | total_len | id | flags/offset |
      ttl | proto | checksum | src | dst
    """
    ihl = (raw[0] & 0x0F) * 4          # header length in bytes
    ttl, proto = raw[8], raw[9]
    src  = ipv4_fmt(raw[12:16])
    dst  = ipv4_fmt(raw[16:20])
    return src, dst, ttl, proto, raw[ihl:]


def parse_tcp(raw: bytes):
    """TCP header — first 14 bytes hold the fields we care about."""
    src_port, dst_port, seq, ack, offset_flags = struct.unpack("!HHLLH", raw[:14])
    offset = ((offset_flags >> 12) & 0xF) * 4
    flag_urg = (offset_flags & 0x020) >> 5
    flag_ack = (offset_flags & 0x010) >> 4
    flag_psh = (offset_flags & 0x008) >> 3
    flag_rst = (offset_flags & 0x004) >> 2
    flag_syn = (offset_flags & 0x002) >> 1
    flag_fin =  offset_flags & 0x001
    flags = {
        "URG": bool(flag_urg), "ACK": bool(flag_ack),
        "PSH": bool(flag_psh), "RST": bool(flag_rst),
        "SYN": bool(flag_syn), "FIN": bool(flag_fin),
    }
    active_flags = [k for k, v in flags.items() if v] or ["—"]
    return src_port, dst_port, seq, ack, active_flags, raw[offset:]


def parse_udp(raw: bytes):
    src_port, dst_port, length = struct.unpack("!HHH", raw[:6])
    return src_port, dst_port, length, raw[8:]


def parse_icmp(raw: bytes):
    icmp_type, code, checksum = struct.unpack("!BBH", raw[:4])
    type_names = {
        0: "Echo Reply", 3: "Dest Unreachable",
        8: "Echo Request", 11: "Time Exceeded",
    }
    return icmp_type, code, checksum, type_names.get(icmp_type, "Unknown"), raw[4:]


# ── payload display ───────────────────────────────────────────────────────────
def format_payload(data: bytes, max_bytes: int = 128) -> str:
    if not data:
        return f"{C.DIM}(empty payload){C.RESET}"

    chunk = data[:max_bytes]
    hex_part = " ".join(f"{b:02x}" for b in chunk)
    try:
        text_part = chunk.decode("utf-8", errors="replace")
        # replace non-printable chars with a dot for readability
        text_part = "".join(c if 32 <= ord(c) < 127 else "." for c in text_part)
    except Exception:
        text_part = "." * len(chunk)

    hex_lines  = textwrap.wrap(hex_part, 47)
    text_lines = textwrap.wrap(text_part, 16)
    rows = []
    for i, (h, t) in enumerate(zip(hex_lines, text_lines)):
        rows.append(f"  {C.DIM}{i*16:04x}{C.RESET}  {C.CYAN}{h:<47}{C.RESET}  {C.GREEN}{t}{C.RESET}")

    if len(data) > max_bytes:
        rows.append(f"  {C.DIM}... {len(data) - max_bytes} more bytes truncated{C.RESET}")

    return "\n".join(rows)


# ── packet counter ────────────────────────────────────────────────────────────
class Stats:
    def __init__(self):
        self.total = 0
        self.tcp   = 0
        self.udp   = 0
        self.icmp  = 0
        self.other = 0

    def show(self):
        print(f"\n{C.BOLD}{C.HEADER}{'─'*60}")
        print("  Session Summary")
        print(f"{'─'*60}{C.RESET}")
        print(f"  Total packets  : {C.BOLD}{self.total}{C.RESET}")
        print(f"  TCP            : {C.GREEN}{self.tcp}{C.RESET}")
        print(f"  UDP            : {C.BLUE}{self.udp}{C.RESET}")
        print(f"  ICMP           : {C.YELLOW}{self.icmp}{C.RESET}")
        print(f"  Other / RAW    : {C.DIM}{self.other}{C.RESET}")
        print(f"{C.BOLD}{C.HEADER}{'─'*60}{C.RESET}\n")


# ── main sniffer loop ─────────────────────────────────────────────────────────
def sniff(packet_limit: int = 0, show_payload: bool = True):

    stats = Stats()

    # Windows raw socket
    try:
        HOST = socket.gethostbyname(socket.gethostname())

        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)

        sock.bind((HOST, 0))

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)

    except PermissionError:
        print(f"{C.RED}[!] Run VS Code as Administrator.{C.RESET}")
        sys.exit(1)

    except Exception as e:
        print(f"{C.RED}[!] Socket Error: {e}{C.RESET}")
        sys.exit(1)

    print(f"\n{C.BOLD}{C.HEADER}{'═'*60}")
    print("     CodeAlpha — Network Packet Sniffer")
    print(f"{'═'*60}{C.RESET}")
    print(f"  Listening on : {HOST}")
    print(f"  Stop with    : Ctrl-C")
    print(f"{C.BOLD}{C.HEADER}{'═'*60}{C.RESET}\n")

    try:
        while True:

            raw_data, _ = sock.recvfrom(65536)

            stats.total += 1

            # Windows packets already start with IP header
            ip_data = raw_data

            try:
                src_ip, dst_ip, ttl, ip_proto, transport_data = parse_ipv4(ip_data)
            except:
                continue

            pkt_no = f"{C.BOLD}#{stats.total:04d}{C.RESET}"

            # TCP
            if ip_proto == 6:

                stats.tcp += 1

                try:
                    sp, dp, seq, ack, flags, payload = parse_tcp(transport_data)
                except:
                    continue

                print(
                    f"{pkt_no} {C.GREEN}TCP{C.RESET} "
                    f"{src_ip}:{sp} → {dst_ip}:{dp}"
                )

            # UDP
            elif ip_proto == 17:

                stats.udp += 1

                try:
                    sp, dp, length, payload = parse_udp(transport_data)
                except:
                    continue

                print(
                    f"{pkt_no} {C.BLUE}UDP{C.RESET} "
                    f"{src_ip}:{sp} → {dst_ip}:{dp}"
                )

            # ICMP
            elif ip_proto == 1:

                stats.icmp += 1

                print(
                    f"{pkt_no} {C.YELLOW}ICMP{C.RESET} "
                    f"{src_ip} → {dst_ip}"
                )

            if packet_limit and stats.total >= packet_limit:
                break

    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}[!] Stopped by user.{C.RESET}")

    finally:

        try:
            sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        except:
            pass

        sock.close()

        stats.show()


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="CodeAlpha — Basic Network Sniffer (no third-party deps)"
    )

    parser.add_argument(
        "-n", "--count", type=int, default=100,
        help="Number of packets to capture (0 = unlimited)"
    )

    parser.add_argument(
        "--no-payload", action="store_true",
        help="Suppress payload hex dump"
    )

    args = parser.parse_args()

    sniff(packet_limit=args.count, show_payload=not args.no_payload)