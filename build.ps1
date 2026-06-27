uv pip install pyinstaller
.venv\Scripts\pyinstaller --noconfirm --onedir --windowed --add-data "app;app" --add-data "media;media" --add-binary "libmpv-2.dll;." --icon "media\assets\app_icon.ico" --name "UngDungHocTap" main.py
Copy-Item "hoctap.db" -Destination "dist\UngDungHocTap\"
