@echo off
setlocal

py -m pip install --upgrade pip pyinstaller
py -m pip install PySide6
py -m pip install psutil
py -m pip install Pillow

if not exist "app_icon.ico" (
  py -c "from PIL import Image, ImageDraw; im=Image.new('RGBA',(256,256),(43,124,255,255)); d=ImageDraw.Draw(im); d.rounded_rectangle((20,20,236,236), radius=40, fill=(28,39,64,255)); d.ellipse((62,62,194,194), outline=(255,255,255,230), width=14); d.line((128,46,128,86), fill=(255,255,255,230), width=10); d.line((128,170,128,210), fill=(255,255,255,230), width=10); im.save('app_icon.ico', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])"
)

py -m PyInstaller --noconfirm --clean DiskHealthMonitor.spec

echo.
echo Build complete. Output: dist\DiskHealthMonitor\
endlocal
