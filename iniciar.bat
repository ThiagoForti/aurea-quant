@echo off
title Aurea Quant - Inicializador Inteligente
chcp 65001 > nul
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1

echo ===================================================
echo           AUREA QUANT - WEALTH MANAGEMENT
echo ===================================================
echo Verificando ambiente Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado neste computador!
    echo Por favor, instale o Python em python.org e marque a opcao "Add python.exe to PATH".
    pause
    exit /b 1
)

echo Fechando sessoes antigas na porta 8501...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

echo Verificando dependencias...
python -c "import streamlit, pandas, plotly, yfinance, openpyxl" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando bibliotecas necessarias pela primeira vez...
    echo Isso pode levar de 1 a 2 minutos. Aguarde...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao instalar dependencias.
        pause
        exit /b 1
    )
    echo Dependencias instaladas com sucesso!
)

echo Iniciando Aurea Quant...
if exist "Iniciar_Aurea_Quant.exe" (
    start "" "Iniciar_Aurea_Quant.exe"
) else (
    start "" python -m streamlit run dashboard.py
)
exit /b 0
