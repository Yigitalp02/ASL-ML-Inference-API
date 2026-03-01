# ASL ML API Deployment Script for Windows
# Uploads files to server and deploys via SSH

param(
    [Parameter(Mandatory=$false)]
    [string]$ServerIP = "192.168.50.100",
    
    [Parameter(Mandatory=$false)]
    [string]$ServerUser = "bilgin",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipUpload = $false
)

$ErrorActionPreference = "Stop"

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "ASL ML API Deployment Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if SSH is available
try {
    $null = Get-Command ssh -ErrorAction Stop
} catch {
    Write-Host "ERROR: SSH not found. Please install OpenSSH." -ForegroundColor Red
    exit 1
}

# Check if SCP is available
try {
    $null = Get-Command scp -ErrorAction Stop
} catch {
    Write-Host "ERROR: SCP not found. Please install OpenSSH." -ForegroundColor Red
    exit 1
}

$SERVER = "${ServerUser}@${ServerIP}"
$SCRIPT_DIR = $PSScriptRoot
# Prefer 97% model, fall back to 96%, then legacy
$MODEL_97PCT   = Join-Path $SCRIPT_DIR "..\iot-sign-glove\models\rf_asl_15letters_normalized_97pct_seed1_feb26.pkl"
$MODEL_96PCT   = Join-Path $SCRIPT_DIR "..\iot-sign-glove\models\rf_asl_15letters_normalized_96pct_seed1.pkl"
$LEGACY_MODEL  = Join-Path $SCRIPT_DIR "..\iot-sign-glove\models\rf_asl_15letters.pkl"
$MODEL_PATH = if (Test-Path $MODEL_97PCT) { $MODEL_97PCT } elseif (Test-Path $MODEL_96PCT) { $MODEL_96PCT } else { $LEGACY_MODEL }

Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow

# Check if model exists
if (-Not (Test-Path $MODEL_PATH)) {
    Write-Host "WARNING: Model not found at: $MODEL_PATH" -ForegroundColor Red
    Write-Host "Deployment will continue, but you need to upload the model manually." -ForegroundColor Yellow
    $MODEL_EXISTS = $false
} else {
    $modelName = [System.IO.Path]::GetFileName($MODEL_PATH)
    Write-Host "  [OK] Model found: $modelName" -ForegroundColor Green
    $MODEL_EXISTS = $true
}

# Test SSH connection
Write-Host "`n[2/7] Testing SSH connection to $SERVER..." -ForegroundColor Yellow
try {
    ssh -o ConnectTimeout=5 $SERVER "echo 'Connection successful'" | Out-Null
    Write-Host "  [OK] SSH connection successful" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] SSH connection failed" -ForegroundColor Red
    Write-Host "  Please check your SSH access to the server." -ForegroundColor Red
    exit 1
}

if (-Not $SkipUpload) {
    # Clean up old upload first
    Write-Host "`n[3/7] Cleaning previous upload..." -ForegroundColor Yellow
    ssh $SERVER "rm -rf /tmp/asl-ml-server /tmp/setup-server.sh /tmp/*.pkl"
    
    # Upload project files
    Write-Host "[3/7] Uploading project files..." -ForegroundColor Yellow
    scp -r "$SCRIPT_DIR" "${SERVER}:/tmp/asl-ml-server"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Upload failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "  [OK] Files uploaded to /tmp/asl-ml-server" -ForegroundColor Green

    # Upload model keeping its original filename
    if ($MODEL_EXISTS) {
        $modelFileName = [System.IO.Path]::GetFileName($MODEL_PATH)
        Write-Host "`n[4/7] Uploading ML model ($modelFileName)..." -ForegroundColor Yellow
        scp "$MODEL_PATH" "${SERVER}:/tmp/$modelFileName"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [ERROR] Model upload failed" -ForegroundColor Red
            exit 1
        }
        Write-Host "  [OK] Model uploaded as $modelFileName" -ForegroundColor Green
    } else {
        Write-Host "`n[4/7] Skipping model upload (not found)" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[3/7] Skipping upload (--SkipUpload flag)" -ForegroundColor Yellow
    Write-Host "[4/7] Skipping model upload" -ForegroundColor Yellow
}

# Execute deployment on server
Write-Host "`n[5/7] Setting up directories on server..." -ForegroundColor Yellow
Write-Host "  Note: You'll be prompted for sudo password" -ForegroundColor Yellow

# Upload the setup script and run it on the server (avoids nested quoting issues)
$modelFileName = [System.IO.Path]::GetFileName($MODEL_PATH)
scp "$SCRIPT_DIR\setup-server.sh" "${SERVER}:/tmp/setup-server.sh"
ssh $SERVER "sed -i 's/\r//' /tmp/setup-server.sh"
ssh -t $SERVER "bash /tmp/setup-server.sh '$modelFileName'"

if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] Setup failed" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Setup complete" -ForegroundColor Green

# Build and start containers
Write-Host "`n[6/7] Building and starting containers..." -ForegroundColor Yellow
Write-Host "  This may take 2-3 minutes..." -ForegroundColor Yellow

# Build and start (one sudo session)
ssh -t $SERVER "cd /opt/stack && echo '  -> Building asl-ml-api container' && sudo docker compose build asl-ml-api && echo '  -> Starting services' && sudo docker compose up -d asl-postgres asl-ml-api && echo '  -> Waiting for services to start...' && sleep 5"

if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] Container startup failed" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Containers started" -ForegroundColor Green

# Test the API
Write-Host "`n[7/7] Testing API..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    $response = Invoke-RestMethod -Uri "http://${ServerIP}:8200/health" -Method Get -TimeoutSec 10
    Write-Host "  [OK] API is responding" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Status: $($response.status)" -ForegroundColor Green
    Write-Host "  Model: $($response.model_name)" -ForegroundColor Green
    $dbStatus = if ($response.database_connected) { "Connected" } else { "Not connected" }
    $dbColor = if ($response.database_connected) { "Green" } else { "Yellow" }
    Write-Host "  Database: $dbStatus" -ForegroundColor $dbColor
} catch {
    Write-Host "  [ERROR] API health check failed" -ForegroundColor Red
    Write-Host "  Check logs: ssh $SERVER `"sudo docker compose logs -f asl-ml-api`"" -ForegroundColor Yellow
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Local API:  http://${ServerIP}:8200" -ForegroundColor Green
Write-Host "Public API: https://asl.ybilgin.com" -ForegroundColor Green
Write-Host "API Docs:   http://${ServerIP}:8200/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Configure Cloudflare Tunnel (see DEPLOYMENT_GUIDE.md)" -ForegroundColor White
Write-Host "  2. Test prediction: curl -X POST http://${ServerIP}:8200/predict ..." -ForegroundColor White
Write-Host "  3. Update desktop app to use API endpoint" -ForegroundColor White
Write-Host ""
Write-Host "View logs:" -ForegroundColor Yellow
Write-Host "  ssh $SERVER `"sudo docker compose logs -f asl-ml-api`"" -ForegroundColor White
Write-Host ""

