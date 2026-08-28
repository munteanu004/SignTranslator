Write-Host "🚀 Starting SignTranslator Backend..." -ForegroundColor Green

cd "C:\Users\user\Desktop\OneDrive\Documents\SignTranslator\backend_api"

# Verifică dacă Flask este instalat
if (-not (python -c "import flask" 2>$null)) {
    Write-Host "📦 Installing Flask..." -ForegroundColor Yellow
    pip install flask flask-cors
}

Write-Host "✅ Starting Flask server..." -ForegroundColor Green
python api_server.py
