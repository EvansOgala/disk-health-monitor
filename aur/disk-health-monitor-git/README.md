# disk-health-monitor-git AUR Staging Folder

This folder mirrors the package files intended for the AUR repository.

Files to publish:

- `PKGBUILD`
- `.SRCINFO`

Typical workflow:

```bash
git clone ssh://aur@aur.archlinux.org/disk-health-monitor-git.git
cd disk-health-monitor-git
cp /path/to/your/source/repo/aur/disk-health-monitor-git/PKGBUILD .
cp /path/to/your/source/repo/aur/disk-health-monitor-git/.SRCINFO .
git add PKGBUILD .SRCINFO
git commit -m "Initial import"
git push
```
