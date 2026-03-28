import json
import re
import shutil
import subprocess
import sys
import time


def get_system_stats(ping_address="1.1.1.1", ping_count=3):
    """Get system stats: RAM, CPU, 1.1.1.1 ping time"""
    if sys.platform != "linux":
        return None, None, None, None

    # ram
    with open("/proc/meminfo") as f:
        meminfo = f.read()
    def parse_kb(key):
        match = re.search(rf"^{key}:\s+(\d+)\s+kB", meminfo, re.MULTILINE)
        return int(match.group(1)) if match else 0
    ram_available = round(parse_kb("MemAvailable") / 1024, 2)
    ram_total = round(parse_kb("MemTotal") / 1024, 2)
    ram_used = round(ram_total - ram_available, 2)

    # cpu usage
    try:
        def read_cpu_times():
            with open("/proc/stat") as f:
                line = f.readline()
            fields = line.split()
            total = sum(int(x) for x in fields[1:])
            idle = int(fields[4])
            return total, idle
        total1, idle1 = read_cpu_times()
        time.sleep(0.5)
        total2, idle2 = read_cpu_times()
        delta_total = total2 - total1
        delta_idle = idle2 - idle1
        cpu_used = round((1 - delta_idle / delta_total) * 100, 2) if delta_total else 0.0
    except PermissionError:
        cpu_used = None

    # ping
    try:
        result = subprocess.run(
            ["ping", "-c", str(ping_count), "-W", "2", ping_address],
            capture_output=True, text=True, timeout=ping_count*3, check=True,
        ) # rtt min/avg/max/mdev
        match = re.search(r"rtt .* = [\d.]+/([\d.]+)/", result.stdout)   # match avg
        ping = float(match.group(1)) if match else None
    except Exception:
        ping = None

    # uptime
    result = subprocess.run(["uptime", "-p"], capture_output=True, text=True, shell=False, check=True)
    uptime = result.stdout.strip()[3:]

    return ram_used, ram_total, cpu_used, ping, uptime


def get_termux_battery():
    """Get termux battery percentage """
    if not shutil.which("termux-battery-status"):
        return None, None, None, None, None
    try:
        result = subprocess.run(["termux-battery-status"], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return data["status"].capitalize(), data.get("percentage", 0), round(data.get("voltage", 0) / 1000, 2), int(data.get("current, 0") / 1000), data.get("temperature", 0)
    except Exception:
        return None, None, None, None, None
