import os
import re
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class DiskInfo:
    device: str
    model: str
    protocol: str
    size: str
    rotational: str


@dataclass
class DiskHealth:
    device: str
    model: str
    protocol: str
    size: str
    health: str
    temp_c: int | None
    power_on_hours: int | None
    alerts: list[str]
    details: str


def _run(cmd: list[str], timeout: int = 40) -> tuple[int, str]:
    try:
        c = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)
    out = (c.stdout or "") + (c.stderr or "")
    return c.returncode, out.strip()


def _needs_root(code: int, output: str) -> bool:
    if code == 0:
        return False
    text = (output or "").lower()
    checks = (
        "permission denied",
        "operation not permitted",
        "root privileges",
        "must be root",
        "are you root",
    )
    return any(key in text for key in checks)


def _run_with_optional_pkexec(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    code, out = _run(cmd, timeout=timeout)
    if not _needs_root(code, out):
        return code, out

    if os.geteuid() == 0:
        return code, out

    if shutil.which("pkexec") is None:
        return code, out

    # Retry with policykit elevation when available.
    return _run(["pkexec", *cmd], timeout=max(timeout, 90))


def _parse_temp(text: str) -> int | None:
    patterns = [
        r"Temperature_Celsius\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)",
        r"Current Drive Temperature:\s*(\d+)",
        r"Temperature:\s*(\d+)\s*C",
        r"temperature\s*:\s*(\d+)\s*C",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


def _parse_power_on_hours(text: str) -> int | None:
    patterns = [
        r"Power_On_Hours\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)",
        r"Accumulated power on time, hours:minutes\s*(\d+):\d+",
        r"Power on Hours:\s*(\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


def _parse_smart_health(text: str) -> str:
    if not text:
        return "Unknown"
    if "PASSED" in text.upper():
        return "PASSED"
    if "FAILED" in text.upper() or "FAILING" in text.upper():
        return "FAILED"
    if "OK" in text.upper():
        return "OK"
    return "Unknown"


def list_disks() -> list[DiskInfo]:
    if not shutil.which("lsblk"):
        return []

    cmd = ["lsblk", "-dn", "-o", "NAME,TYPE,MODEL,TRAN,ROTA,SIZE"]
    code, out = _run(cmd)
    if code != 0:
        return []

    disks: list[DiskInfo] = []
    for line in out.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        name, dev_type, model, tran, rota, size = parts
        if dev_type != "disk":
            continue
        protocol = tran if tran != "-" else ("sata" if rota in {"0", "1"} else "unknown")
        rotational = "hdd" if rota == "1" else "ssd"
        disks.append(
            DiskInfo(
                device=f"/dev/{name}",
                model=model if model != "-" else "Unknown",
                protocol=protocol,
                size=size,
                rotational=rotational,
            )
        )

    disks.sort(key=lambda d: d.device)
    return disks


def _health_smartctl(device: str) -> tuple[str, int | None, int | None, str]:
    if not shutil.which("smartctl"):
        return "Unknown", None, None, "smartctl not found"

    code, out = _run_with_optional_pkexec(["smartctl", "-H", "-A", device], timeout=60)
    if code not in {0, 2}:  # smartctl often returns 2 for prefail bits/info
        return "Unknown", None, None, out or "smartctl failed"

    health = _parse_smart_health(out)
    temp = _parse_temp(out)
    poh = _parse_power_on_hours(out)
    return health, temp, poh, out


def _health_nvme(device: str) -> tuple[str, int | None, int | None, str]:
    if not shutil.which("nvme"):
        return "Unknown", None, None, "nvme-cli not found"

    code, out = _run_with_optional_pkexec(["nvme", "smart-log", device], timeout=45)
    if code != 0:
        return "Unknown", None, None, out or "nvme smart-log failed"

    health = "OK"
    m_warn = re.search(r"critical_warning\s*:\s*(\d+)", out)
    if m_warn:
        try:
            if int(m_warn.group(1)) != 0:
                health = "WARN"
        except ValueError:
            pass

    temp = _parse_temp(out)
    poh = _parse_power_on_hours(out)
    if poh is None:
        m_hours = re.search(r"power_on_hours\s*:\s*(\d+)", out)
        if m_hours:
            try:
                poh = int(m_hours.group(1))
            except ValueError:
                pass

    return health, temp, poh, out


def read_all_disk_health(alert_temp_c: int = 60) -> list[DiskHealth]:
    rows: list[DiskHealth] = []
    for disk in list_disks():
        if "nvme" in disk.device:
            health, temp, poh, details = _health_nvme(disk.device)
            if health == "Unknown":
                health2, temp2, poh2, details2 = _health_smartctl(disk.device)
                if health2 != "Unknown" or details2:
                    health, temp, poh, details = health2, temp2, poh2, details2
        else:
            health, temp, poh, details = _health_smartctl(disk.device)

        alerts: list[str] = []
        if health in {"FAILED", "WARN"}:
            alerts.append(f"health={health}")
        if temp is not None and temp >= alert_temp_c:
            alerts.append(f"temp>={alert_temp_c}C")
        if _needs_root(1, details) and not alerts:
            alerts.append("root-required")

        rows.append(
            DiskHealth(
                device=disk.device,
                model=disk.model,
                protocol=f"{disk.protocol}/{disk.rotational}",
                size=disk.size,
                health=health,
                temp_c=temp,
                power_on_hours=poh,
                alerts=alerts,
                details=details,
            )
        )

    return rows


def launch_in_terminal(command: str, title: str = "Disk Health Monitor") -> tuple[bool, str]:
    shell_cmd = (
        f"echo '[{title}]'; echo; {command}; rc=$?; echo; "
        "if [ $rc -eq 0 ]; then echo Done.; else echo Failed with exit code $rc.; fi; "
        "echo; read -r -p 'Press Enter to close...' _"
    )

    terminals = [
        ["x-terminal-emulator", "-e", "bash", "-lc", shell_cmd],
        ["gnome-terminal", "--", "bash", "-lc", shell_cmd],
        ["konsole", "-e", "bash", "-lc", shell_cmd],
        ["xfce4-terminal", "-x", "bash", "-lc", shell_cmd],
        ["kitty", "bash", "-lc", shell_cmd],
        ["alacritty", "-e", "bash", "-lc", shell_cmd],
        ["xterm", "-e", "bash", "-lc", shell_cmd],
    ]

    for cmd in terminals:
        if shutil.which(cmd[0]) is None:
            continue
        try:
            subprocess.Popen(cmd)
            return True, f"Launched in terminal: {command}"
        except Exception:  # noqa: BLE001
            continue

    return False, "No supported terminal emulator found."
