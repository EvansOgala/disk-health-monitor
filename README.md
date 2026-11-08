# Disk Health Monitor

Disk Health Monitor is a desktop utility for checking SMART and NVMe drive health, temperatures, and trend history. It includes a PySide6 interface and a separate native GNOME/libadwaita interface.

## Features

- Detects local block devices
- SMART health checks for SATA and SAS drives
- NVMe SMART log checks for NVMe drives
- Temperature and health trend snapshots
- Launch detailed SMART command output in a terminal
- Qt desktop UI on Linux and Windows
- Optional native libadwaita UI for GNOME

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

### GNOME / libadwaita variant

Install the GTK bindings and run the alternate frontend:

```bash
sudo pacman -S --needed python-gobject gtk4 libadwaita
python3 gtk_main.py
```

After installing the AUR package, start it with `disk-health-monitor-gtk` or choose **Disk Health Monitor (GNOME)** in the app launcher. The libadwaita interface follows the desktop color scheme.

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
