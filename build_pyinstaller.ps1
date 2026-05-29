# Build script for Hushline using PyInstaller
# Run from project root with the virtualenv activated.

$distName = "Hushline"
$iconPath = "assets\hushline.ico" # adjust if you have an icon

# Add data entries (source;dest) - semicolon separator on Windows
$addData = @(
    "ambient_settings.json;.",
    "ui;ui",
    "ui\widgets;ui\widgets",
    "media;media"
)
$addDataArgs = $addData | ForEach-Object { "--add-data `"$_`"" } | Join-String " "

pyinstaller --noconfirm --clean --onedir --name $distName --icon $iconPath $addDataArgs main.py
