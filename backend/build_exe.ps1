# 프론트엔드 + 백엔드를 하나의 exe로 묶는 빌드 스크립트.
# 사전 준비 (최초 1회):
#   cd frontend; npm install
#   cd backend; python -m venv .venv; .venv\Scripts\pip install -r requirements.txt pyinstaller
#
# 사용법: backend 폴더에서 실행
#   .\build_exe.ps1
# 결과물: backend\dist\FleaMarketLayout.exe (이 파일 하나만 배포하면 됨)

# 주의: npm/pyinstaller 같은 외부 실행 파일은 정상 동작 중에도 stderr에 로그를 씀.
# PowerShell 5.1에서 $ErrorActionPreference = "Stop"을 걸어두면 그 stderr 줄마다 종료 오류로
# 취급돼버려 정상 빌드도 멈추므로, 대신 각 단계 후 $LASTEXITCODE를 직접 확인한다.

Write-Host "1) 프론트엔드 빌드 중..."
Push-Location ..\frontend
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "프론트엔드 빌드 실패 (exit $LASTEXITCODE)" }
Pop-Location

Write-Host "2) OpenSSL DLL 위치 확인 중..."
# conda/miniforge 계열 Python은 _ssl이 의존하는 libssl/libcrypto DLL이 venv 밖(Library\bin)에 있어서
# PyInstaller가 자동으로 못 찾는 경우가 있다. 있으면 --add-binary로 명시적으로 넣어준다.
$pythonExe = ".\.venv\Scripts\python.exe"
# venv 자체(sys.prefix)가 아니라 venv를 만든 원본 conda/miniforge 설치 경로(sys.base_prefix)에
# Library\bin이 있다 - venv 폴더 안에는 없다.
$baseRoot = & $pythonExe -c "import sys; print(sys.base_prefix)"
$condaLibBin = Join-Path $baseRoot "Library\bin"

$extraBinaries = @()
if (Test-Path (Join-Path $condaLibBin "libssl-3-x64.dll")) {
    $extraBinaries += "--add-binary"
    $extraBinaries += "$condaLibBin\libssl-3-x64.dll;."
    $extraBinaries += "--add-binary"
    $extraBinaries += "$condaLibBin\libcrypto-3-x64.dll;."
    Write-Host "   conda 계열 OpenSSL DLL 발견, 번들에 포함합니다."
} else {
    Write-Host "   conda 계열 OpenSSL DLL 없음 (표준 Python이면 정상, 그냥 진행)."
}

Write-Host "3) PyInstaller로 exe 빌드 중..."
& $pythonExe -m PyInstaller --onefile --name FleaMarketLayout `
    --add-data "..\frontend\dist;static" `
    @extraBinaries `
    run_desktop.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 빌드 실패 (exit $LASTEXITCODE)" }

Write-Host "완료: dist\FleaMarketLayout.exe"
