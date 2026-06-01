# 🚀 Deployment Guide: Render

## Overview
This guide walks through deploying the **Sports Card Tagger** FastAPI application to [Render](https://render.com) with a PostgreSQL database.

---

## ✅ Prerequisites

Before you start, ensure you have:

1. **GitHub Account** - Code must be in a Git repository
2. **Render Account** - Free tier available at https://render.com
3. **Credentials Ready:**
   - Collector Investor API username and base64-encoded token
   - Azure OpenAI endpoint, deployment name, and API key
   - PostgreSQL password (generated on Render)

---

## 📋 Step-by-Step Deployment

### **Step 1: Prepare Your Git Repository**

Ensure your code is pushed to GitHub:

```bash
# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Sports Card Tagger"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push to main branch
git branch -M main
git push -u origin main
```

**Important:** Make sure `.env` file is in `.gitignore` (never commit secrets):

```bash
# Check if .gitignore exists
cat .gitignore

# If not, create it with:
echo ".env" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "venv/" >> .gitignore
```

---

### **Step 2: Create a Render Account**

1. Go to https://render.com
2. Sign up with GitHub (recommended for easier integration)
3. Verify your email

---

### **Step 3: Create PostgreSQL Database on Render**

#### **Option A: Using render.yaml (Recommended)**

If you have `render.yaml` in your repo root, Render will automatically create both database and web service.

#### **Option B: Manual Creation**

1. Go to Render Dashboard → **New +** → **PostgreSQL**
2. Fill in details:
   - **Name:** `sports-card-db`
   - **Database:** `sports_card_tagger`
   - **User:** `sports_card_user`
   - **Region:** Choose closest to you (e.g., Oregon, Frankfurt)
   - **PostgreSQL Version:** 14 (or higher)
   - **Plan:** Free or Standard (Starter is sufficient for dev)

3. Click **Create Database**
4. **Wait 2-3 minutes** for the database to be provisioned
5. Copy the **Internal Database URL** (you'll need this)

**Example URL format:**
```
postgresql://sports_card_user:YOUR_PASSWORD@dpg-xxx.render.internal:5432/sports_card_tagger
```

---

### **Step 4: Create Web Service on Render**

#### **From render.yaml (Automatic)**

1. Go to Render Dashboard → **New +** → **Web Service**
2. Select **Deploy an existing GitHub repo**
3. Connect your GitHub account and select this repository
4. Render will automatically detect `render.yaml` and configure everything

#### **Manual Creation**

1. Go to Render Dashboard → **New +** → **Web Service**
2. Click **Deploy an existing GitHub repo** → **GitHub** → Select your repo
3. Fill in details:
   - **Name:** `sports-card-tagger-api`
   - **Root Directory:** (leave empty)
   - **Environment:** `Python 3`
   - **Region:** Same as database
   - **Branch:** `main`

4. **Build Command:**
   ```bash
   pip install -r requirements.txt && python -c "from src.storage import init_db; init_db()"
   ```

5. **Start Command:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

6. Click **Create Web Service**

---

### **Step 5: Configure Environment Variables**

After creating the web service, add environment variables:

1. Go to your Render Dashboard
2. Select **sports-card-tagger-api** service
3. Click **Environment** tab
4. Add the following variables:

#### **Database Variables** (Auto-populated if using render.yaml)
```
DB_HOST             → Render internal host
DB_PORT             → 5432
DB_NAME             → sports_card_tagger
DB_USER             → sports_card_user
DB_PASSWORD         → Copy from PostgreSQL service page
DATABASE_URL        → postgresql://user:pass@host:5432/database
```

#### **Collector Investor API**
```
COLLECTOR_INVESTOR_USERNAME       → Your CI username
COLLECTOR_INVESTOR_BASE64_TOKEN   → Your CI base64 token
```

#### **Azure OpenAI**
```
AZURE_OPENAI_ENDPOINT             → https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT           → gpt-4-vision
AZURE_OPENAI_API_KEY              → Your Azure API key
```

#### **Tag Generation Settings**
```
TAG_COUNT_MIN                      → 40
TAG_COUNT_MAX                      → 50
TAG_TEMPERATURE                    → 0.3
TAG_MAX_TOKENS                     → 800
```

---

### **Step 6: Deploy**

#### **Option A: Auto-Deploy from Git Push (Recommended)**

1. Every push to `main` branch auto-deploys:
   ```bash
   git add .
   git commit -m "Update tagging logic"
   git push origin main
   ```

2. Render automatically triggers a new build
3. Check deployment status in Render Dashboard

#### **Option B: Manual Deploy**

1. Go to web service on Render Dashboard
2. Click **Manual Deploy** → **Deploy Latest Commit**
3. Watch build logs in real-time

---

### **Step 7: Verify Deployment**

#### **Check Service Health**

1. Get your service URL from Render Dashboard (e.g., `https://sports-card-tagger-api.onrender.com`)
2. Visit health check endpoint:
   ```
   https://sports-card-tagger-api.onrender.com/
   ```
   Should return: `{"status": "ok", "products_in_db": 0}`

#### **View Live Logs**

1. Go to web service on Render Dashboard
2. Click **Logs** tab
3. Real-time deployment and runtime logs appear

#### **Test API Endpoint**

```bash
# Test the pipeline endpoint
curl -X POST https://sports-card-tagger-api.onrender.com/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "offset": 0,
    "limit": 5,
    "event_id": "4053663",
    "timeout": 45
  }'

# Search endpoint
curl "https://sports-card-tagger-api.onrender.com/search?q=michael+jordan"
```

---

## 🔒 Security Best Practices

1. **Never commit .env file:**
   ```bash
   echo ".env" >> .gitignore
   git add .gitignore
   git commit -m "Add .env to gitignore"
   ```

2. **Use render.yaml for secrets:**
   - Environment variables defined in Render UI are encrypted at rest
   - Not visible in code or logs

3. **Rotate credentials regularly:**
   - Update Collector Investor token every 90 days
   - Rotate Azure OpenAI API key periodically

4. **Enable database backups:**
   - PostgreSQL on Render: Go to Database → **Backups** → Enable
   - Free tier has daily backups for 7 days

---

## 🛠️ Common Issues & Troubleshooting

### **Issue 1: Build fails with `ModuleNotFoundError`**

**Solution:**
```bash
# Ensure requirements.txt is complete
pip freeze > requirements.txt
git add requirements.txt
git push origin main
```

### **Issue 2: Database connection fails**

**Check:**
1. `DATABASE_URL` environment variable is set correctly
2. Database service is running (Check Render Dashboard)
3. PostgreSQL credentials are correct

```bash
# Test connection locally
psql postgresql://user:password@host:5432/database
```

### **Issue 3: "Address already in use" error**

**Solution:** Render auto-assigns `$PORT`. Your start command must use it:
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### **Issue 4: API key errors (Azure OpenAI / Collector Investor)**

**Solution:**
1. Double-check credentials in Render Environment Variables
2. Test locally with same credentials:
   ```bash
   source .env  # Load from .env
   python -c "from src.services.tagger_service import generate_tags; print('OK')"
   ```

### **Issue 5: Deployment stuck in "Deploy in progress"**

**Solution:**
1. Go to web service → **Manual Deploy** → **Clear Build Cache**
2. Try deploying again

---

## 📊 Monitoring & Maintenance

### **View Real-Time Logs**
```
Render Dashboard → sports-card-tagger-api → Logs
```

### **Check Database Size**
```sql
-- Connect to PostgreSQL
SELECT pg_size_pretty(pg_database_size('sports_card_tagger'));
```

### **Database Cleanup**
```sql
-- See tagging history
SELECT COUNT(*) FROM tagging_history;

-- Delete old records (if needed)
DELETE FROM tagging_history 
WHERE tagged_at < NOW() - INTERVAL '30 days';
```

### **Restart Service**
```
Render Dashboard → sports-card-tagger-api → Settings → Restart Instance
```

---

## 🚀 Auto-Scaling & Performance

### **Recommended Setup for Production:**

| Metric | Free Tier | Standard |
|--------|-----------|----------|
| Web Service | $0/mo | $7/mo |
| PostgreSQL | $0/mo (shuts down after 15 min inactivity) | $15/mo |
| Max Concurrency | 1 instance | Multiple instances |
| Storage | 250MB | Configurable |

**For high-volume tagging:**
1. Upgrade PostgreSQL plan in Render Dashboard
2. Add background worker service for async tagging:
   ```bash
   # Create new service with same environment
   Start Command: python background_worker.py
   ```

---

## 📝 Example: Full Pipeline on Production

Once deployed:

```bash
# Production API Base URL
API_BASE="https://sports-card-tagger-api.onrender.com"

# Fetch products, generate tags, post to API (one shot)
curl -X POST $API_BASE/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "4053663",
    "offset": 0,
    "limit": 50,
    "timeout": 45
  }'

# Search for tagged products
curl "$API_BASE/search?q=rookie%20card"

# Get all products
curl "$API_BASE/products"

# Get specific product with tags
curl "$API_BASE/products/12345/tags"
```

---

## 🆘 Need Help?

- **Render Docs:** https://render.com/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **PostgreSQL Docs:** https://www.postgresql.org/docs
- **GitHub Issues:** Create an issue in your repository

---

## ✨ Next Steps After Deployment

1. **Set up GitHub Actions CI/CD** (optional):
   - Auto-run tests on every push
   - Auto-deploy on successful tests

2. **Add monitoring:**
   - Render alerts on service health
   - Database performance monitoring

3. **Scale up:**
   - Upgrade to Standard/Professional plans
   - Add background job queue for bulk tagging

4. **API Documentation:**
   - Visit `https://your-api.onrender.com/docs` for interactive Swagger UI
   - Visit `https://your-api.onrender.com/redoc` for ReDoc documentation

---

**Deployment Date:** {{ DEPLOYMENT_DATE }}
**Last Updated:** June 2026
