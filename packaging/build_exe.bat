@echo off
rem Submarine Saga - Copyright (c) 2024-2026 Faiaz Abrar Zaman Pronoy and
rem Sinthia Khandoker. All rights reserved. See LICENSE.
rem Builds a stand-alone Windows version of Submarine Saga that runs
rem without Python installed. The result is packaging\dist\SubmarineSaga\,
rem zipped as packaging\dist\SubmarineSaga-Windows.zip for sharing.
rem
rem Needs Python 3 and, once: python -m pip install pyinstaller
cd /d "%~dp0.."

python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo PyInstaller is not installed. Run:  python -m pip install pyinstaller
    pause
    exit /b 1
)

rem --collect-all OpenGL takes the whole bundled PyOpenGL package, including
rem the freeglut DLL in OpenGL\DLLS that glutInit needs; PyOpenGL loads its
rem platform modules by name at run time, so PyInstaller cannot find them alone.
python -m PyInstaller --noconfirm --clean --windowed --onedir ^
    --name SubmarineSaga ^
    --icon "%~dp0icon.ico" ^
    --version-file "%~dp0version_info.txt" ^
    --collect-all OpenGL ^
    --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0build" ^
    "Submarine Saga (CSE423 Project).py"
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

copy /y README.md "%~dp0dist\SubmarineSaga\README.md" >nul
copy /y LICENSE "%~dp0dist\SubmarineSaga\LICENSE.txt" >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path '%~dp0dist\SubmarineSaga' -DestinationPath '%~dp0dist\SubmarineSaga-Windows.zip'"
echo.
echo Done: packaging\dist\SubmarineSaga\SubmarineSaga.exe
echo       packaging\dist\SubmarineSaga-Windows.zip
