# MCP Tools Debugging Guide

## Quick Test Links

### 1. Test HTML Page
Open in browser: `file:///C:/Users/cchampio/mcp_poc/test-tools.html`
- Tests tools endpoint directly from browser
- Shows timing and detailed logs
- Click "Test 5 Sequential Requests" to verify stability

### 2. Backend Test Endpoints
- **Full Test Suite**: http://localhost:8100/test/all
- **Tool Listing Test**: http://localhost:8100/test/tools-list
- **Tool Call Test**: http://localhost:8100/test/tool-call
- **Production Tools**: http://localhost:8100/tools

### 3. Frontend
- **Main App**: http://localhost:3000

## Comprehensive Logging

All components now have detailed logging with prefixes:

### Backend Logs (docker-compose logs orchestrator)
- `[TOOLS]` - Tool listing operations
- `[TEST-*]` - Test endpoint execution
- `[EXECUTOR]` - Tool execution details
- `[PARAM-ENHANCE]` - Parameter enhancement with LLM
- Timing information for all operations

### Frontend Logs (Browser Console)
- `[TOOLS-PANEL]` - Tools panel operations
- Shows:
  - Fetch attempts and retries
  - Response timing
  - Error details
  - Retry countdown

## Features Added

### 1. Auto-Retry with Backoff
- 3 attempts total
- 1s delay, then 2s delay
- Shows "Retrying... (attempt X/3)" during retry
- Detailed error messages on failure

### 2. Request Timeouts
- Backend: 10s for tool listing, 30s for execution
- Frontend: 10s for all requests
- Errors propagate properly (no silent failures)

### 3. Enhanced Error Messages
- Shows HTTP status codes
- Displays backend error details
- Counts retry attempts
- Detailed console logging

## Debugging Steps

### Step 1: Verify Backend
```bash
# Test backend directly
curl http://localhost:8100/test/all

# Expected: {"overall_status": "success", ...}
```

### Step 2: Check Browser Console
1. Open http://localhost:3000
2. Press F12 to open DevTools
3. Go to Console tab
4. Look for `[TOOLS-PANEL]` logs
5. Check for any red error messages

### Step 3: Monitor Docker Logs
```bash
# Watch orchestrator logs in real-time
docker-compose logs -f orchestrator

# Watch all services
docker-compose logs -f
```

### Step 4: Check Network Tab
1. Open DevTools (F12)
2. Go to Network tab
3. Refresh page
4. Look for `/tools` request
5. Check:
   - Status code (should be 200)
   - Response time
   - Response data

## Common Issues & Solutions

### Issue: "Works once then fails"
**Possible Causes:**
1. Browser caching - Clear cache and hard refresh (Ctrl+Shift+R)
2. CORS issues - Check browser console for CORS errors
3. Network timeout - Check timing in Network tab

**Solutions:**
- Use test HTML page to isolate issue
- Check browser console for specific errors
- Monitor docker logs during failure

### Issue: Slow Response
**Check:**
- MCP server status: `docker-compose ps mcp-server`
- Orchestrator logs for timeout messages
- Network tab for actual timing

**Thresholds:**
- Tool listing should be < 1s
- Tool calls should be < 2s
- Retries happen if > 10s

### Issue: CORS Errors
**Check:**
- Frontend env vars in docker-compose.yml
- Browser console for specific CORS error
- Network tab shows OPTIONS preflight request

**Fix:**
- Verify VITE_ORCHESTRATOR_URL=http://localhost:8100
- Check CORS middleware in app.py (should allow all origins in dev)

## Logs to Share When Reporting Issues

1. **Browser Console Logs**
   - Press F12 → Console tab
   - Copy all `[TOOLS-PANEL]` messages

2. **Backend Logs**
   ```bash
   docker-compose logs --tail=100 orchestrator > orchestrator.log
   ```

3. **Network Tab**
   - Screenshot of failed `/tools` request
   - Include Headers, Response, Timing tabs

4. **Test Results**
   - Output from http://localhost:8100/test/all
   - Results from test-tools.html

## Health Checks

### Quick Health Check
```bash
# All should return 200 OK
curl -I http://localhost:8100/tools
curl -I http://localhost:8100/test/tools-list
curl http://localhost:8000/health  # MCP server (if added)
```

### Full Stack Status
```bash
docker-compose ps
# All services should be "Up" and "healthy"

docker-compose logs --tail=10 mcp-server orchestrator frontend
# Look for any ERROR or exception messages
```

## Expected Behavior

### First Load
1. Frontend: `[TOOLS-PANEL] Starting to fetch tools...`
2. Frontend: `[TOOLS-PANEL] Fetching from URL: http://localhost:8100/tools`
3. Backend: `[TOOLS] GET /tools endpoint called`
4. Backend: `[TOOLS] Connected to MCP server, listing tools...`
5. Backend: `[TOOLS] Successfully converted 4 tools`
6. Frontend: `[TOOLS-PANEL] ✅ Tools state updated successfully`
7. UI: Shows 4 tools with icons ◈, ⟁, ◉, ⌘

### Refresh/Subsequent Loads
- Same as above
- Should complete in < 1s
- No errors or retries

### Error Scenario
1. Frontend tries request
2. If fails: `[TOOLS-PANEL] ❌ Fetch failed (attempt 1)`
3. Frontend: `[TOOLS-PANEL] Retrying in 1000ms...`
4. UI shows: "Retrying... (attempt 2/3)"
5. After 3 attempts: Shows error message

## Performance Benchmarks

From test suite (http://localhost:8100/test/all):
- **Tool Listing**: ~0.5s (4 tools)
- **Tool Call** (echo): ~0.13s
- **Connection Time**: ~0.04s

If you see significantly different numbers, something is wrong.
