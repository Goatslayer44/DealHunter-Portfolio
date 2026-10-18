"""Beginner-friendly authentication log analyzer.

Reads fictional authentication logs and flags:
  1. IP addresses with repeated failed logins
  2. Usernames with repeated failed logins
  3. Successful logins that follow multiple failures from the same IP

Log line format (one event per line):
    YYYY-MM-DD HH:MM:SS <FAILED|SUCCESS> user=<name> ip=<address>

Only the Python standard library is used.
"""
import argparse
import ipaddress
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

DEFAULT_THRESHOLD = 5  # Failures needed before activity is called suspicious.
MAX_LINE_LENGTH = 500  # Longer lines are treated as malformed.

LINE_PATTERN = re.compile(
    r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) "
    r"(?P<status>FAILED|SUCCESS) "
    r"user=(?P<user>[A-Za-z0-9_.-]{1,32}) "
    r"ip=(?P<ip>[0-9A-Fa-f:.]{2,45})$"
)


@dataclass(frozen=True)
class LoginEvent:
    timestamp: datetime
    success: bool
    user: str
    ip: str


def parse_line(line):
    """Return a LoginEvent for a valid log line, or None if it is malformed."""
    line = line.strip()
    if not line or len(line) > MAX_LINE_LENGTH:
        return None

    match = LINE_PATTERN.match(line)
    if not match:
        return None

    try:
        timestamp = datetime.strptime(match["time"], "%Y-%m-%d %H:%M:%S")
        ip = str(ipaddress.ip_address(match["ip"]))
    except ValueError:
        return None  # Impossible date/time or invalid IP address.

    return LoginEvent(timestamp, match["status"] == "SUCCESS", match["user"], ip)


def parse_lines(lines):
    """Return (events, malformed_count) for an iterable of log lines.

    Blank lines are ignored; other unreadable lines are counted as malformed.
    """
    events = []
    malformed = 0
    for line in lines:
        if not line.strip():
            continue
        event = parse_line(line)
        if event is None:
            malformed += 1
        else:
            events.append(event)
    return events, malformed


def analyze(events, threshold=DEFAULT_THRESHOLD):
    """Return a dict of findings for a list of LoginEvent objects."""
    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
        raise ValueError("threshold must be a whole number of at least 1")

    events = sorted(events, key=lambda e: e.timestamp)
    failures_by_ip = Counter()
    failures_by_user = Counter()
    failures_so_far = defaultdict(int)  # failures seen per IP so far
    success_after_failures = []

    for event in events:
        if event.success:
            prior = failures_so_far[event.ip]
            if prior >= threshold:
                success_after_failures.append(
                    {"ip": event.ip, "user": event.user,
                     "time": event.timestamp, "prior_failures": prior}
                )
        else:
            failures_by_ip[event.ip] += 1
            failures_by_user[event.user] += 1
            failures_so_far[event.ip] += 1

    return {
        "total_events": len(events),
        "suspicious_ips": {ip: n for ip, n in failures_by_ip.most_common() if n >= threshold},
        "targeted_users": {u: n for u, n in failures_by_user.most_common() if n >= threshold},
        "success_after_failures": success_after_failures,
    }


def analyze_file(path, threshold=DEFAULT_THRESHOLD):
    """Read a log file and return (findings, malformed_count)."""
    with open(path, encoding="utf-8", errors="replace") as log_file:
        events, malformed = parse_lines(log_file)
    return analyze(events, threshold), malformed


def format_report(findings, malformed, threshold):
    """Return a readable text report."""
    lines = [
        "SECURITY LOG REPORT (fictional sample data)",
        "-------------------------------------------",
        f"Valid events analyzed: {findings['total_events']}",
        f"Malformed lines skipped: {malformed}",
        f"Threshold: {threshold} failed logins",
        "",
        "Suspicious IP addresses:",
    ]
    if findings["suspicious_ips"]:
        lines += [f"  {ip}: {n} failed logins" for ip, n in findings["suspicious_ips"].items()]
    else:
        lines.append("  None found")

    lines += ["", "Usernames with repeated failures:"]
    if findings["targeted_users"]:
        lines += [f"  {u}: {n} failed logins" for u, n in findings["targeted_users"].items()]
    else:
        lines.append("  None found")

    lines += ["", "Successful logins after multiple failures (review these first):"]
    if findings["success_after_failures"]:
        for item in findings["success_after_failures"]:
            lines.append(
                f"  {item['time']} user={item['user']} ip={item['ip']} "
                f"after {item['prior_failures']} failures"
            )
    else:
        lines.append("  None found")

    lines += ["", "Note: these are leads for a human to review, not proof of an attack."]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze a fictional authentication log.")
    parser.add_argument("logfile", help="path to the log file")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                        help=f"failed logins before flagging (default {DEFAULT_THRESHOLD})")
    args = parser.parse_args(argv)

    try:
        findings, malformed = analyze_file(args.logfile, args.threshold)
    except OSError as error:
        print(f"Could not read log file: {error}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Invalid option: {error}", file=sys.stderr)
        return 2

    print(format_report(findings, malformed, args.threshold))
    return 0


if __name__ == "__main__":
    sys.exit(main())
