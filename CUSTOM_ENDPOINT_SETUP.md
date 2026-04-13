# Custom API Endpoint Setup Guide

Your website needs a custom endpoint that returns your auction products in a format the tag generator can consume.

## Endpoint Specification

### URL
```
GET https://bid.collectorinvestorauctions.com/api/products
```

### Response Format (JSON Array)
```json
[
  {
    "id": 4398706,
    "name": "2018 Topps Update Chrome Shohei Ohtani RC XFractor 23/99 PSA 10",
    "description": "Rookie card of Shohei Ohtani, Chrome XFractor parallel, numbered 23/99, graded PSA 10 Gem Mint",
    "category": "Baseball",
    "image_url": "https://bid.collectorinvestorauctions.com/images/lot/4398706.jpg"
  },
  {
    "id": 4311539,
    "name": "2016 National Treasures #5 Steph Curry 48/49 BGS 9 Auto 10",
    "description": "Steph Curry National Treasures card, numbered 48/49, BGS 9 with Auto grade 10",
    "category": "Basketball",
    "image_url": "https://bid.collectorinvestorauctions.com/images/lot/4311539.jpg"
  }
]
```

### Required Fields
- `id` (integer): Unique lot/product ID
- `name` (string): Product name/title
- `description` (string): Product description
- `category` (string): Sport/category (e.g., "Baseball", "Basketball", "Football")
- `image_url` (string, optional): Full URL to product image

### Optional Query Parameters
```
GET /api/products?status=active         # Only active lots
GET /api/products?limit=100             # Limit results
GET /api/products?offset=0              # Pagination
GET /api/products?category=Baseball     # Filter by category
```

---

## Implementation Examples

### Option 1: ASP.NET Core (Recommended for your site)

If your site is built with ASP.NET (CultureUpdate platform), add this controller:

```csharp
using Microsoft.AspNetCore.Mvc;
using System.Collections.Generic;
using System.Linq;
using YourNamespace.Models;  // Your existing models

namespace YourNamespace.Api
{
    [ApiController]
    [Route("api/[controller]")]
    [Produces("application/json")]
    public class ProductsController : ControllerBase
    {
        private readonly ILotService _lotService;  // Your existing service

        public ProductsController(ILotService lotService)
        {
            _lotService = lotService;
        }

        /// <summary>
        /// Get all active auction lots as products for AI tagging
        /// </summary>
        [HttpGet]
        public ActionResult<List<ProductDto>> GetProducts(
            [FromQuery] string status = "active",
            [FromQuery] int limit = 500,
            [FromQuery] int offset = 0)
        {
            try
            {
                var lots = _lotService.GetLots(
                    status: status,
                    limit: limit,
                    offset: offset
                );

                var products = lots.Select(lot => new ProductDto
                {
                    Id = lot.LotId,
                    Name = lot.Title,
                    Description = lot.Description ?? "",
                    Category = lot.Category ?? "Sports Cards",
                    ImageUrl = lot.PrimaryImageUrl ?? lot.ThumbnailUrl
                }).ToList();

                return Ok(products);
            }
            catch (Exception ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }
    }

    public class ProductDto
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Description { get; set; }
        public string Category { get; set; }
        public string ImageUrl { get; set; }
    }
}
```

**Startup Registration** (in `Startup.cs` or `Program.cs`):
```csharp
services.AddControllers();
// Add to endpoints
app.MapControllers();
```

---

### Option 2: Node.js / Express

```javascript
const express = require('express');
const router = express.Router();
const db = require('./database');  // Your DB connection

// GET /api/products
router.get('/products', async (req, res) => {
    try {
        const { status = 'active', limit = 500, offset = 0 } = req.query;

        // Query your lots table
        const lots = await db.query(`
            SELECT 
                lot_id as id,
                title as name,
                description,
                category,
                image_url
            FROM auctions_lots
            WHERE status = ?
            LIMIT ? OFFSET ?
        `, [status, limit, offset]);

        // Map to product format
        const products = lots.map(lot => ({
            id: lot.id,
            name: lot.name,
            description: lot.description || '',
            category: lot.category || 'Sports Cards',
            image_url: lot.image_url
        }));

        res.json(products);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;
```

**Register in app.js:**
```javascript
app.use('/api', require('./routes/products'));
```

---

### Option 3: Python / Flask

```python
from flask import Flask, request, jsonify
from your_database import get_lots  # Your existing function

app = Flask(__name__)

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        status = request.args.get('status', 'active')
        limit = request.args.get('limit', 500, type=int)
        offset = request.args.get('offset', 0, type=int)

        # Get lots from your database
        lots = get_lots(status=status, limit=limit, offset=offset)

        # Convert to product format
        products = [
            {
                'id': lot['lot_id'],
                'name': lot['title'],
                'description': lot['description'] or '',
                'category': lot['category'] or 'Sports Cards',
                'image_url': lot['image_url']
            }
            for lot in lots
        ]

        return jsonify(products)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)
```

---

### Option 4: PHP / Laravel

```php
<?php

namespace App\Http\Controllers;

use App\Models\Lot;
use Illuminate\Http\Request;

class ProductController extends Controller
{
    public function index(Request $request)
    {
        $status = $request->input('status', 'active');
        $limit = $request->input('limit', 500);
        $offset = $request->input('offset', 0);

        $lots = Lot::where('status', $status)
            ->limit($limit)
            ->offset($offset)
            ->get();

        $products = $lots->map(function ($lot) {
            return [
                'id' => $lot->lot_id,
                'name' => $lot->title,
                'description' => $lot->description ?? '',
                'category' => $lot->category ?? 'Sports Cards',
                'image_url' => $lot->primary_image_url
            ];
        });

        return response()->json($products);
    }
}

// In routes/api.php
Route::get('/products', 'ProductController@index');
```

---

## Testing Your Endpoint

Once deployed, test with:

```bash
# Get first 10 products
curl "https://bid.collectorinvestorauctions.com/api/products?limit=10"

# Get only baseball cards
curl "https://bid.collectorinvestorauctions.com/api/products?category=Baseball"

# Check response format
curl "https://bid.collectorinvestorauctions.com/api/products?limit=1" | jq .
```

---

## Using With the Tagger

Once your endpoint is ready, use it like this:

```bash
# Option 1: Direct API call
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"api_url": "https://bid.collectorinvestorauctions.com/api/products"}'

# Option 2: With filters
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"api_url": "https://bid.collectorinvestorauctions.com/api/products?status=active&limit=50"}'
```

---

## Pagination Example

If you have many products, paginate:

```bash
# Get first page
curl "https://bid.collectorinvestorauctions.com/api/products?limit=100&offset=0"

# Get next page
curl "https://bid.collectorinvestorauctions.com/api/products?limit=100&offset=100"
```

Then in Python, create a script to paginate and tag all products:

```python
import requests
from requests.auth import HTTPBasicAuth

API_URL = "https://bid.collectorinvestorauctions.com/api/products"
PAGE_SIZE = 100
limit = PAGE_SIZE
offset = 0

all_products = []

while True:
    response = requests.get(f"{API_URL}?limit={limit}&offset={offset}")
    products = response.json()
    
    if not products:
        break
    
    all_products.extend(products)
    offset += limit

print(f"Total products: {len(all_products)}")

# Save to file
import json
with open('all_products.json', 'w') as f:
    json.dump(all_products, f, indent=2)

# Then tag using tagger
# python main.py with file_path="all_products.json"
```

---

## Security Notes

- **Authentication**: If endpoint needs auth, use HTTP Basic or Bearer token
- **Rate Limiting**: Consider adding rate limits to your endpoint
- **CORS**: Make sure CORS is enabled if accessed from different domain
- **Data Privacy**: Don't expose sensitive auction data (bids, bidder info, etc.)

---

## Support

If you need help implementing the endpoint, provide:
1. What backend/framework your site uses
2. Current database schema for lots/products
3. Any existing API patterns I should follow
