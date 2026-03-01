# Disk Health Monitor

Python desktop app for SMART/NVMe disk health monitoring.

## Features

- Detect local disks via `lsblk`.
- SMART/NVMe health checks (`smartctl`, `nvme-cli`).
- Temperature alerts and health warnings.
- Trend history for temperature and health snapshots.
- Themed rounded UI (dark/light).

## Run

```bash
cd /home/evans/Documents/disk-health-monitor
python3 main.py
```

## Notes

- Install `smartmontools` for SMART checks.
- Install `nvme-cli` for NVMe smart-log support.
- Some devices require root for full SMART data.

## Build AppImage

```bash
cd /home/evans/Documents/disk-health-monitor
python3 -m pip install --user pyinstaller
# place appimagetool at ./tools/appimagetool.AppImage or install appimagetool in PATH
./build-appimage.sh
```
