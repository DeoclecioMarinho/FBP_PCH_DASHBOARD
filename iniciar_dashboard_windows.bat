@echo off
chcp 65001 >nul
title PCH-FBP | Painel de Controlo
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Nao foi possivel instalar as dependencias. Verifique a ligacao a Internet e a versao do Python.
  pause
  exit /b 1
)
py -m streamlit run app.py
pause
