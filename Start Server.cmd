@echo off
wt -d "C:\TextRPG" powershell -NoExit -Command "uvicorn main:app --port 8001 --reload"