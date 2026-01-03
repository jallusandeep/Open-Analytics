# Troubleshooting Guide

This guide covers common issues and their solutions when running Rubik Analytics.

## Backend Issues

### Port Already in Use

**Symptoms:**
- Error: `[Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)`
- Server fails to start

**Solutions:**

1. **Stop existing processes:**
   ```batch
   server\windows\stop-all.bat
   ```

2. **Find and kill process manually:**
   ```batch
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```

3. **Wait and retry:**
   ```batch
   timeout /t 5
   server\windows\start-all.bat
   ```

### Server Needs Restart After Code Changes

**Symptoms:**
- 404 errors on new/updated routes
- Changes not reflected in running server

**Solution:**

Restart the backend server:

```bash
# Stop server (Ctrl+C in terminal)
# Then restart:
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the restart script:
```batch
server\windows\restart-all.bat
```

Verify routes are registered:
- Visit: http://localhost:8000/health
- Check `script_endpoints` array in response

### Database Connection Failed

**Symptoms:**
- `[ERROR] Auth database connection failed`
- `[ERROR] Analytics database connection failed`

**Solutions:**

1. **Check data directory exists:**
   ```batch
   dir data\auth\sqlite
   dir data\analytics\duckdb
   ```

2. **Create missing directories:**
   ```batch
   mkdir data\auth\sqlite
   mkdir data\analytics\duckdb
   ```

3. **Check file permissions:**
   - Ensure write access to data directory
   - Check if files are locked by another process

4. **Reinitialize database:**
   ```batch
   cd backend
   venv\Scripts\python.exe scripts\init\init_auth_database.py
   ```

### Backend Not Reachable from Frontend

**Symptoms:**
- "Unable to connect to server" error
- Network errors in browser console

**Solutions:**

1. **Verify backend is running:**
   ```bash
   # Check health endpoint
   curl http://localhost:8000/health
   # Or open in browser: http://localhost:8000/docs
   ```

2. **Check API URL configuration:**
   - Frontend uses: `NEXT_PUBLIC_API_URL` environment variable
   - Default: `http://localhost:8000`
   - Verify in `frontend/.env.local` if customized

3. **Check CORS settings:**
   - Backend CORS should allow `http://localhost:3000`
   - Check `backend/app/main.py` CORS configuration

4. **Restart both servers:**
   ```batch
   server\windows\restart-all.bat
   ```

### Script Save Connection Error

**Symptoms:**
- "Backend server not running" when backend IS running
- Errors when saving transformation scripts

**Solutions:**

1. **Check error type:**
   - **No HTTP response** → Backend truly unreachable (check if running)
   - **401 Unauthorized** → Session expired, login again
   - **403 Forbidden** → Permission denied
   - **404 Not Found** → Endpoint doesn't exist (check route registration)
   - **500 Server Error** → Check backend console for errors

2. **Verify script endpoint:**
   ```bash
   # Check if endpoint is registered
   curl http://localhost:8000/health
   # Look for script endpoints in response
   ```

3. **Check backend logs:**
   - Look at backend console for errors
   - Check for import errors or route registration issues

### Bcrypt Compatibility Error

**Symptoms:**
- `AttributeError: module 'bcrypt' has no attribute '__about__'`
- `ValueError: password cannot be longer than 72 bytes`

**Solutions:**

1. **Downgrade bcrypt:**
   ```batch
   cd backend
   venv\Scripts\python.exe -m pip uninstall bcrypt
   venv\Scripts\python.exe -m pip install "bcrypt<5.0.0"
   ```

2. **Verify installation:**
   ```batch
   venv\Scripts\python.exe -m pip show bcrypt
   ```

### Missing Dependencies

**Symptoms:**
- `ModuleNotFoundError: No module named 'uvicorn'`
- Import errors

**Solutions:**

1. **Reinstall dependencies:**
   ```batch
   cd backend
   venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. **Check virtual environment:**
   ```batch
   venv\Scripts\python.exe --version
   ```

3. **Verify activation:**
   - Ensure virtual environment is activated before running commands
   - Check prompt shows `(venv)` prefix

## Frontend Issues

### Build Errors

**Symptoms:**
- TypeScript errors during build
- Missing module errors

**Solutions:**

1. **Clean and reinstall:**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **Check TypeScript version:**
   ```bash
   npm list typescript
   ```

### Port 3000 Already in Use

**Symptoms:**
- Error: Port 3000 is already in use

**Solutions:**

1. **Stop existing Next.js server:**
   ```batch
   server\windows\stop-all.bat
   ```

2. **Find and kill process:**
   ```batch
   netstat -ano | findstr :3000
   taskkill /PID <PID> /F
   ```

### API Errors in Browser Console

**Symptoms:**
- CORS errors
- 401/403 errors
- Network errors

**Solutions:**

1. **Check authentication:**
   - Verify you're logged in
   - Check for `auth_token` cookie in browser DevTools
   - Log out and log back in if token expired

2. **Check backend CORS:**
   - Verify backend allows frontend origin
   - Check `backend/app/main.py` CORS configuration

3. **Check API base URL:**
   - Verify `NEXT_PUBLIC_API_URL` environment variable
   - Check browser console for actual API calls

## Database Issues

### Migration Errors

**Symptoms:**
- Schema mismatch errors
- Missing column errors

**Solutions:**

1. **Run migration scripts:**
   ```batch
   cd backend
   venv\Scripts\python.exe scripts\migrations\migrate_core_schema.py
   venv\Scripts\python.exe scripts\migrations\migrate_accounts_schema.py
   venv\Scripts\python.exe scripts\migrations\migrate_symbols_schema.py
   ```

2. **Check database schema:**
   - Verify tables exist
   - Check column definitions match models

### Stuck Uploads

**Symptoms:**
- Uploads stuck in PENDING status
- Uploads not completing

**Solutions:**

1. **Run fix script:**
   ```batch
   cd backend
   venv\Scripts\python.exe scripts\maintenance\run_system_maintenance.py fix-uploads
   ```

2. **Check upload logs:**
   - Review upload log entries
   - Check for errors in log details

## Authentication Issues

### Cannot Login

**Symptoms:**
- Invalid credentials error
- Login fails

**Solutions:**

1. **Check default credentials:**
   - Username: `admin`
   - Password: `admin123`

2. **Reset super user:**
   ```batch
   cd backend
   server\windows\fix-super-user.bat
   ```

3. **Verify user exists:**
   ```batch
   cd backend
   venv\Scripts\python.exe scripts\maintenance\run_system_maintenance.py super-users
   ```

### Session Expired

**Symptoms:**
- 401 Unauthorized errors
- Forced to login repeatedly

**Solutions:**

1. **Clear browser cookies:**
   - Delete `auth_token` cookie
   - Log in again

2. **Check token expiration:**
   - Default: 8 hours
   - Can be configured in `backend/app/core/config.py`

## Getting Help

If issues persist:

1. **Check logs:**
   - Backend console output
   - Browser console (F12)
   - Network tab for API calls

2. **Verify setup:**
   - Run `server\windows\backend-setup.bat`
   - Run `server\windows\frontend-setup.bat`

3. **Database diagnostics:**
   ```batch
   cd backend
   venv\Scripts\python.exe scripts\maintenance\run_system_maintenance.py db
   venv\Scripts\python.exe scripts\maintenance\run_system_maintenance.py users
   ```

4. **Review documentation:**
   - [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
   - [PROJECT-STRUCTURE.md](./PROJECT-STRUCTURE.md) for folder structure
   - [QUICK-START.md](./QUICK-START.md) for setup and deployment
