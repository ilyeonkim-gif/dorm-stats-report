@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo  생활관 통계보고서 - Windows 빌드
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] Python 버전 확인...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo    https://www.python.org 에서 Python 설치
    echo    설치할 때 "Add python.exe to PATH" 반드시 체크
    pause
    exit /b 1
)
python --version

echo.
echo [2/4] PyInstaller 및 의존성 설치...
python -m pip install --upgrade pip pyinstaller flask olefile openpyxl -q
if errorlevel 1 (
    echo ❌ 의존성 설치 실패
    pause
    exit /b 1
)
echo ✅ 설치 완료

echo.
echo [3/4] PyInstaller로 .exe 빌드 중...
echo    (처음에는 1-2분 소요될 수 있습니다)
pyinstaller pyinstaller.spec --clean
if errorlevel 1 (
    echo ❌ 빌드 실패
    pause
    exit /b 1
)
echo ✅ 빌드 완료

echo.
echo [4/4] 결과 확인...
if exist "dist\생활관통계보고서.exe" (
    echo ✅ 빌드 성공!
    echo.
    echo 📁 생성 위치: dist\생활관통계보고서.exe
    echo 📦 배포용: dist 폴더 전체를 압축
    echo.
    echo 다음 명령어로 바로 테스트 가능:
    echo    dist\생활관통계보고서.exe
    echo.
    pause
) else (
    echo ❌ 빌드 결과를 찾을 수 없습니다
    pause
    exit /b 1
)
