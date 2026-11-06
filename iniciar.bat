@echo off
chcp 65001 >nul
rem iniciar.bat - Prepara el entorno y ejecuta o compila GitCraft en Windows.
rem   iniciar.bat              Instala dependencias y abre la app
rem   iniciar.bat --compilar   Genera un ejecutable en dist\gitcraft.exe
setlocal
cd /d "%~dp0"

set "VENV=.venv"
set "MODO=%~1"

if /i "%MODO%"=="-h" set "MODO=--ayuda"
if /i "%MODO%"=="--help" set "MODO=--ayuda"
if /i "%MODO%"=="-c" set "MODO=--compilar"

if /i "%MODO%"=="--ayuda" (
    echo iniciar.bat              Instala dependencias y abre la app
    echo iniciar.bat --compilar   Genera un ejecutable en dist\gitcraft.exe
    exit /b 0
)

if not "%MODO%"=="" if /i not "%MODO%"=="--compilar" (
    echo Opción desconocida: %MODO% ^(usa --ayuda^) 1>&2
    exit /b 1
)

rem Usa el launcher "py" si existe, si no "python"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"

if not exist "%VENV%\Scripts\python.exe" (
    echo -- Creando entorno virtual...
    %PY% -m venv "%VENV%" || (
        echo No se pudo crear el entorno virtual. Verifica que Python este instalado y en el PATH.
        pause
        exit /b 1
    )
)

echo -- Instalando dependencias...
"%VENV%\Scripts\python.exe" -m pip install --quiet --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install --quiet -r requirements.txt || (
    echo Error instalando dependencias.
    pause
    exit /b 1
)

if /i "%MODO%"=="--compilar" (
    "%VENV%\Scripts\python.exe" -m pip install --quiet pyinstaller
    echo -- Compilando...
    "%VENV%\Scripts\pyinstaller.exe" --noconfirm --clean --onefile --windowed --name gitcraft main.py || (
        echo Error al compilar.
        pause
        exit /b 1
    )
    echo -- Listo: dist\gitcraft.exe
    exit /b 0
)

echo -- Iniciando GitCraft...
"%VENV%\Scripts\python.exe" main.py
if errorlevel 1 pause
endlocal
