# Disk Health Monitor

Disk Health Monitor is a Qt desktop utility for checking SMART and NVMe drive health, temperatures, and trend history.

## Features

- Detects local block devices
- SMART health checks for SATA and SAS drives
- NVMe SMART log checks for NVMe drives
- Temperature and health trend snapshots
- Launch detailed SMART command output in a terminal
- Qt desktop UI on Linux and Windows

## Runtime Dependencies

- Python 3
- Qt for Python (PySide6)
- smartmontools (`smartctl`)
- nvme-cli (`nvme`) for NVMe details
- A supported terminal emulator for detailed command output
- Optional: `pkexec` for elevated reads without running the whole app as root

On Arch Linux:

```bash
sudo pacman -S --needed python pyside6 smartmontools nvme-cli polkit xterm
```

## Run From Source

```bash
cd ~/Documents/disk-health-monitor
python3 main.py
```

## Packaging

This repository now includes an AUR-ready `disk-health-monitor-git` package:

- [PKGBUILD](./PKGBUILD)
- [.SRCINFO](./.SRCINFO)

To build it locally on Arch Linux:

```bash
cd ~/Documents/disk-health-monitor
makepkg -si
```

## Notes

- SMART reads may require elevated privileges depending on your drive and kernel permissions.
- The app stores settings in `~/.config/disk_health_monitor/settings.json`.

## License

MIT
