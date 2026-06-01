# 🚀 RENDER DEPLOYMENT QUICK START

## Your Sports Card Tagger is Ready for Render!

This file provides a quick checklist to get your app live in 10 minutes.

---

## ✅ Pre-Deployment Checklist

- [ ] **GitHub Repository Created** - Code is pushed to GitHub (public or private)
- [ ] **Credentials Gathered:**
  - [ ] Collector Investor API: `COLLECTOR_INVESTOR_USERNAME`
  - [ ] Collector Investor API: `COLLECTOR_INVESTOR_BASE64_TOKEN`
  - [ ] Azure OpenAI: `AZURE_OPENAI_ENDPOINT`
  - [ ] Azure OpenAI: `AZURE_OPENAI_DEPLOYMENT`
  - [ ] Azure OpenAI: `AZURE_OPENAI_API_KEY`
- [ ] **Files in Repository:**
  - [ ] `render.yaml` ✓ (Created)
  - [ ] `.env.example` ✓ (Created)
  - [ ] `runtime.txt` ✓ (Created)
  - [ ] `requirements.txt` ✓ (Exists)
  - [ ] `main.py` ✓ (Exists)
  - [ ] `.gitignore` ✓ (Exists with `.env`)

---

## 🎯 5-Minute Setup

### **1. Go to Render (5 seconds)**
- Open https://render.com
- Sign up with GitHub (if not already signed in)

### **2. Deploy from render.yaml (2 minutes)**
- Click **New +** → **Web Service** → **Deploy via Blueprint**
- Select your GitHub repository
- Click **Create from Blueprint**
- Render will automatically:
  - Create PostgreSQL database
  - Create FastAPI web service
  - Set up basic environment variables

### **3. Add Credentials (3 minutes)**
Go to **Web Service Settings** → **Environment** and add:

```
COLLECTOR_INVESTOR_USERNAME=your_value
COLLECTOR_INVESTOR_BASE64_TOKEN=your_value
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4-vision
AZURE_OPENAI_API_KEY=your_value
TAG_COUNT_MIN=40
TAG_COUNT_MAX=50
TAG_TEMPERATURE=0.3
TAG_MAX_TOKENS=800
```

### **4. Deploy! (1 minute)**
- Render auto-deploys from render.yaml
- Watch logs: **Logs** tab in dashboard
- Wait ~5 minutes for first deployment

### **5. Test Your API (30 seconds)**
```bash
# Get your URL from Render Dashboard (e.g., sports-card-tagger-api.onrender.com)

# Health check
curl https://sports-card-tagger-api.onrender.com/

# Interactive API docs
https://sports-card-tagger-api.onrender.com/docs
```

---

## 📚 Detailed Guide

For complete step-by-step instructions, see **[DEPLOY.md](./DEPLOY.md)**

---

## 🔥 Next: Make First API Call

Once deployed, test the pipeline:

```bash
API="https://sports-card-tagger-api.onrender.com"

curl -X POST $API/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "4053663",
    "offset": 0,
    "limit": 5,
    "timeout": 45
  }'
```

Expected response:
```json
{
  "success": true,
  "fetched": 5,
  "products_tagged": 5,
  "total_tags": 245,
  "tags_posted": 5,
  "tags_posted_failed": 0
}
```

---

## 📊 What You Get

| Component | Details |
|-----------|---------|
| **API URL** | `https://sports-card-tagger-api.onrender.com` |
| **Interactive Docs** | `/docs` (Swagger UI) |
| **API Spec** | `/redoc` (ReDoc) |
| **Database** | PostgreSQL (managed by Render) |
| **SSL/TLS** | Free HTTPS included |
| **Monitoring** | Real-time logs + health checks |
| **Auto-Deploy** | Every git push to main |

---

## 🛠️ Troubleshooting

**Q: Build failed?**
- Check Logs tab for errors
- Ensure all environment variables are set
- Run locally first: `uvicorn main:app --reload`

**Q: Database connection error?**
- Verify DATABASE_URL is set in environment
- Check PostgreSQL service is running
- Test connection: `psql $DATABASE_URL`

**Q: Deployment takes too long?**
- First deployment: 5-10 minutes (normal)
- Subsequent deployments: 2-3 minutes
- Check Logs tab for build progress

**More help?** See [DEPLOY.md](./DEPLOY.md) - Troubleshooting section

---

## 📝 Environment Variables Reference

| Variable | Example | Required |
|----------|---------|----------|
| `DATABASE_URL` | `postgresql://user:pass@host/db` | Auto (from render.yaml) |
| `COLLECTOR_INVESTOR_USERNAME` | `john@example.com` | ✅ Yes |
| `COLLECTOR_INVESTOR_BASE64_TOKEN` | `base64_encoded_token` | ✅ Yes |
| `AZURE_OPENAI_ENDPOINT` | `https://xxx.openai.azure.com/` | ✅ Yes |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4-vision` | ✅ Yes |
| `AZURE_OPENAI_API_KEY` | `xxxxxxxx` | ✅ Yes |
| `TAG_COUNT_MIN` | `40` | ❌ No (default: 40) |
| `TAG_COUNT_MAX` | `50` | ❌ No (default: 50) |
| `TAG_TEMPERATURE` | `0.3` | ❌ No (default: 0.3) |
| `TAG_MAX_TOKENS` | `800` | ❌ No (default: 800) |

---

## 🎉 Deployment Complete!

Your **Sports Card Tagger** is now live on Render! 🚀

- **Monitor:** Check Logs for real-time activity
- **Update:** Push to `main` branch for auto-deployment
- **Scale:** Upgrade plan as your usage grows
- **Share:** Your API is public at `https://sports-card-tagger-api.onrender.com`

---

**Questions?** Check [DEPLOY.md](./DEPLOY.md) for detailed troubleshooting and best practices.
