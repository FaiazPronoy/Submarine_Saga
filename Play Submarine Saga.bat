@echo off
rem Submarine Saga - Copyright (c) 2024-2026 Faiaz Abrar Zaman Pronoy and
rem Sinthia Khandoker. All rights reserved. See LICENSE.
rem Double click this file to start Submarine Saga.
title Submarine Saga
cd /d "%~dp0"

rem Prefer the "py" launcher that the Windows Python installer adds, then
rem fall back to whatever "python" is on the PATH.
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo Python was not found on this computer.
    echo Install Python 3 from https://www.python.org/downloads/ and tick
    echo "Add python.exe to PATH" during the install, then run this file again.
    pause
    exit /b 1
)

%PY% "Submarine Saga (CSE423 Project).py"
if errorlevel 1 (
    echo.
    echo The game stopped with an error. The message above says why.
    pause
)
