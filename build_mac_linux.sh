#!/bin/bash
set -e

echo ""
echo "========================================"
echo "  생활관 통계보고서 - macOS/Linux 빌드"
echo "========================================"
echo ""

cd "$(dirname "$0")"

echo "[1/4] Python 버전 확인..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3이 설치되어 있지 않습니다."
    echo "   macOS: brew install python3"
    echo "   Linux(Ubuntu/Debian): sudo apt install python3 python3-pip"
    exit 1
fi
python3 --version

echo ""
echo "[2/4] PyInstaller 및 의존성 설치..."
python3 -m pip install --upgrade pip pyinstaller flask olefile openpyxl -q 2>/dev/null || {
    echo "❌ 의존성 설치 실패"
    exit 1
}
echo "✅ 설치 완료"

echo ""
echo "[3/4] PyInstaller로 빌드 중..."
echo "    (처음에는 1-2분 소요될 수 있습니다)"
python3 -m PyInstaller pyinstaller.spec --clean || {
    echo "❌ 빌드 실패"
    exit 1
}
echo "✅ 빌드 완료"

echo ""
echo "[4/4] 결과 확인..."
if [ -f "dist/생활관통계보고서" ]; then
    echo "✅ 빌드 성공!"
    echo ""
    echo "📁 생성 위치:"
    if [ "$(uname)" == "Darwin" ]; then
        echo "   dist/생활관통계보고서.app/ (macOS)"
        echo ""
        echo "📦 배포용: dist 폴더 전체를 압축"
        echo "   zip -r 생활관통계보고서-macos.zip dist/생활관통계보고서.app"
    else
        echo "   dist/생활관통계보고서 (Linux)"
        echo ""
        echo "📦 배포용: dist 폴더 압축"
        echo "   tar -czf 생활관통계보고서-linux.tar.gz dist/생활관통계보고서/"
    fi
    echo ""
    echo "다음 명령어로 바로 테스트 가능:"
    if [ "$(uname)" == "Darwin" ]; then
        echo "    open dist/생활관통계보고서.app"
    else
        echo "    ./dist/생활관통계보고서/생활관통계보고서"
    fi
    echo ""
else
    echo "❌ 빌드 결과를 찾을 수 없습니다"
    exit 1
fi
