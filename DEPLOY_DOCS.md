# Deploy Enhanced API Documentation

## Steps to Update the Live API Server

### Option 1: Use the Deployment Script (Easiest)

From your Windows machine, run:

```powershell
cd C:\Users\Yigit\Desktop\iot-sign-language-desktop\ASL-ML-Inference-API
.\deploy.ps1
```

This will automatically:
- Upload the files to your server
- Pull the latest changes
- Rebuild the Docker container
- Restart the service

---

### Option 2: Manual Deployment on Server

If you prefer to do it manually, SSH into your server and run:

```bash
# 1. Navigate to the project directory
cd /opt/stack/asl-ml-server

# 2. Pull the latest changes from GitHub
sudo git pull origin main

# 3. Rebuild the Docker image
cd /opt/stack
sudo docker compose build asl-ml-api

# 4. Restart the service
sudo docker compose up -d asl-ml-api

# 5. Check if it's running
sudo docker compose ps asl-ml-api

# 6. View logs to confirm it started successfully
sudo docker compose logs -f asl-ml-api
# Press Ctrl+C to exit logs
```

---

## Verify the Changes

Once deployed, verify the new documentation is live:

1. **Visit the docs**: https://api.ybilgin.com/docs
   - You should see the enhanced descriptions
   - All examples should be visible
   - No emojis or special characters

2. **Test an endpoint**:
   - Click on `POST /predict`
   - Click "Try it out"
   - Use the example data
   - Click "Execute"
   - Verify you get a response

3. **Check health**:
   ```bash
   curl https://api.ybilgin.com/health
   ```

---

## Troubleshooting

### If you see errors after pulling:

```bash
# Check what changed
cd /opt/stack/asl-ml-server
git diff HEAD~1

# If there are conflicts
git stash
git pull origin main
git stash pop

# Force rebuild without cache
sudo docker compose build --no-cache asl-ml-api
sudo docker compose up -d asl-ml-api
```

### If the service won't start:

```bash
# Check detailed logs
sudo docker compose logs asl-ml-api | tail -50

# Check if port is already in use
sudo netstat -tlnp | grep :8000

# Restart the entire stack
sudo docker compose down
sudo docker compose up -d
```

---

## What Will Change

After deployment, users visiting api.ybilgin.com/docs will see:

- ✅ Comprehensive endpoint descriptions
- ✅ Request/response examples for all endpoints  
- ✅ Code examples in multiple languages
- ✅ Clear parameter documentation
- ✅ Interactive "Try it out" functionality
- ✅ Better organized with tags

No breaking changes - existing integrations will continue to work!

