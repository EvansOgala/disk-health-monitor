# Disk Health Monitor

Disk health utility for SMART checks, drive status review, and trend history.

## Features

- Detects local block devices
- SMART health checks for SATA/SAS drives
- NVMe SMART log checks for NVMe drives
- Temperature and health trend snapshots
- Launch detailed SMART command output in terminal
- Linux: GTK4 UI
- Windows: PySide6 UI

## Dependencies

### Runtime

- Python 3.11+

Linux stack:

- GTK4 + PyGObject
- `smartmontools` (`smartctl`)
- `nvme-cli` (`nvme`) for NVMe details
- A supported terminal emulator (`x-terminal-emulator`, `gnome-terminal`, `konsole`, `xfce4-terminal`, `kitty`, `alacritty`, or `xterm`)
- Optional: `pkexec` for privileged reads without starting the app as root

Windows stack:

- PySide6 (Qt)
- Recommended: `smartctl` in `PATH` for SMART health/temperature data
- Optional: `psutil` for richer disk enumeration

Install `smartctl` on Windows:

```powershell
winget install smartmontools.smartmontools
```

Then run Disk Health Monitor from an elevated terminal (Run as Administrator) for best SMART access.

The Windows app can also prompt to relaunch itself as Administrator when SMART access is blocked.

### Install dependencies by distro

#### Arch Linux / Nyarch

```bash
sudo pacman -S --needed python python-gobject gtk4 smartmontools nvme-cli polkit xterm
```

#### Debian / Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-gi gir1.2-gtk-4.0 smartmontools nvme-cli policykit-1 xterm
```

#### Fedora

```bash
sudo dnf install -y python3 python3-gobject gtk4 smartmontools nvme-cli polkit xterm
```

## Run from source

### Linux

```bash
cd /home/'your username'/Documents/disk-health-monitor
python3 main.py
```

### Windows

```powershell
cd C:\Users\your-username\Documents\disk-health-monitor
py -m pip install PySide6 psutil
py main.py
```

## Build AppImage

### Build requirements

```bash
python3 -m pip install --user pyinstaller
```

Install `appimagetool` in `PATH`, or place one of these files in `./tools/`:

- `appimagetool.AppImage`
- `appimagetool-x86_64.AppImage`

### Build command

```bash
cd /home/'your username'/Documents/disk-health-monitor
chmod +x build-appimage.sh
./build-appimage.sh
```

The script outputs an `.AppImage` file in the project root.

## Build Windows (PyInstaller)

```powershell
cd C:\Users\your-username\Documents\disk-health-monitor
build-windows.bat
```

The executable is emitted into `dist\DiskHealthMonitor\`.
