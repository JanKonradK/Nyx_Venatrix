# Docker Desktop WSL2 Integration Setup

## Why This Setup Matters

Running Nyx Venatrix in WSL2 provides the best development experience:
- ✅ Native Linux environment (Python/Node work better)
- ✅ Faster package installations
- ✅ Better shell scripting
- ✅ Playwright/Ray optimized for Linux

**The only catch**: Docker needs a one-time setup to work in WSL2.

---

## Quick Setup (5 minutes)

### Step 1: Open Docker Desktop Settings

1. Right-click the Docker Desktop icon in system tray
2. Click **Settings**

### Step 2: Enable WSL2 Integration

1. Navigate to: **Settings** → **Resources** → **WSL Integration**
2. Toggle ON: **Enable integration with my default WSL distro**
3. Find your Ubuntu distribution in the list (e.g., "Ubuntu", "Ubuntu-22.04")
4. Toggle it **ON**
5. Click **Apply & Restart**

### Step 3: Verify Setup

Open your WSL2 terminal and run:

```bash
docker --version
# Should output: Docker version 29.0.1, build...

docker ps
# Should output: CONTAINER ID   IMAGE...
# (or empty table if no containers running)

docker compose version
# Should output: Docker Compose version v2.x.x
```

✅ If all three commands work, you're done!

---

## Troubleshooting

### Error: "docker: command not found"

**Solution**: Docker Desktop integration is not enabled. Repeat Step 2 above.

### Error: "Cannot connect to Docker daemon"

**Solutions**:
1. Restart Docker Desktop
2. Restart WSL: `wsl --shutdown` in PowerShell, then reopen WSL terminal
3. Check Docker Desktop is running (icon in system tray)

### Docker Desktop Not Installed?

Download from: https://www.docker.com/products/docker-desktop

**Important**: During installation, select **"Use WSL 2 instead of Hyper-V"**

---

## Native Windows vs WSL2 Comparison

| Factor | WSL2 | Native Windows |
|--------|------|----------------|
| Docker Setup | One-time config | Works immediately |
| Python/Node Speed | ✅ Faster | ❌ Slower |
| Shell Scripts | ✅ Bash native | ❌ Needs PowerShell |
| Playwright | ✅ Better | ⚠️ Requires WSL anyway |
| Ray (distributed) | ✅ Optimized | ❌ Limited support |
| File I/O | ✅ Faster | ❌ Slower |
| **Recommendation** | ✅ **Preferred** | Use for Docker only |

---

## After Setup: Run the Project

```bash
# Start infrastructure
docker compose -f docker-compose.db.yml up -d

# Verify services
docker compose -f docker-compose.db.yml ps

# Should show:
# - postgres (port 5432)
# - redis (port 6379)
# - qdrant (port 6333)
```

Now all the mocking/fallbacks are unnecessary - full functionality enabled! 🚀
