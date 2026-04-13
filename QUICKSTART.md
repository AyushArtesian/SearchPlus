# Quick Start Guide

## 1️⃣ Install Dependencies

```bash
cd sports-card-tagger
pip install -r requirements.txt
```

## 2️⃣ Configure OpenAI API Key

Edit `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=sk-YOUR_KEY_HERE
```

Get your key at: https://platform.openai.com/api-keys

## 3️⃣ Start the Server

```bash
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

## 4️⃣ Run the Tagging Pipeline (in another terminal)

### Option A: With Mock Data (Recommended first test)
```bash
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"api_url": null}'
```

### Option B: With Your Own API
```bash
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"api_url": "https://api.yourstore.com/products"}'
```

### Option C: Using Python Test Script
```bash
python test_api.py
```

## 5️⃣ Try Searching

```bash
# Search for fast bowler
curl "http://localhost:8000/search?q=fast+bowler"

# Search for world cup winners
curl "http://localhost:8000/search?q=world+cup"

# Get all products
curl http://localhost:8000/products

# Get specific product
curl http://localhost:8000/products/2

# Get product tags
curl http://localhost:8000/products/2/tags
```

## 📊 What Happens When You Run Pipeline

1. **Fetches products** from the provided API URL (or uses mock data)
2. **Calls GPT-4o** for each product with:
   - Product image (if available)
   - Product name
   - Product description
3. **Generates 15-20 tags** for each product
4. **Saves to `products.json`** immediately (auto-incremental save)
5. **Shows progress** in terminal

Terminal output example:
```
📋 Using mock product data...
🏷️  Tagging 1/5: Virat Kohli - Gold Edition (with image)...
   → Generated 18 tags
🏷️  Tagging 2/5: Jasprit Bumrah - Platinum (with image)...
   → Generated 19 tags
...
✨ Pipeline complete! Tagged 5 products (92 total tags)
```

## 🔍 Search Scoring

Each search result has a score based on:
- **Tag match** = 2 points (query found in AI-generated tags)
- **Name match** = 5 points (query found in product name)
- **Description match** = 1 point
- **Category match** = 1 point

Results are ranked by score (highest first).

## 📁 Output File

After running pipeline, you'll see a `products.json` file containing all products with their AI-generated tags:

```json
[
  {
    "id": 1,
    "name": "Virat Kohli - Gold Edition",
    "category": "Cricket",
    "image_url": "https://...",
    "description": "...",
    "tags": ["virat kohli", "kohli", "rcb", "indian batsman", ...]
  },
  ...
]
```

## 🛠️ Troubleshooting

### "ModuleNotFoundError: No module named 'fastapi'"
→ Run: `pip install -r requirements.txt`

### "Error: OpenAI API key not found"
→ Set `OPENAI_API_KEY` in `.env` file

### "Connection refused" when running test script
→ Make sure server is running: `uvicorn main:app --reload --port 8000`

### "Failed to fetch products from API"
→ Check the API URL is correct and accessible. Pipeline will automatically fall back to mock data.

### GPT-4o calls are slow
→ This is normal! GPT-4o processes images which takes a few seconds per product.

## 📚 API Documentation

### Interactive Docs
Visit: http://localhost:8000/docs (Swagger UI)

### OpenAPI Schema
Visit: http://localhost:8000/openapi.json

## 🚀 Next Steps

1. ✅ Run with mock data first
2. ✅ Try different search queries
3. ✅ Connect your own ecommerce API
4. ✅ Customize GPT-4o prompt in `tagger.py` for your domain
5. ✅ Add database instead of JSON file for production
6. ✅ Add caching to avoid re-tagging products

## 📞 Support

For issues with:
- **FastAPI**: https://fastapi.tiangolo.com
- **OpenAI GPT-4o**: https://platform.openai.com/docs/guides/vision
- **Uvicorn**: https://www.uvicorn.org
