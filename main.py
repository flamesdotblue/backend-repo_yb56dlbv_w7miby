import os
from typing import List, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HotelResponse(BaseModel):
    id: str
    name: str
    location: str
    rating: float
    reviews: int
    image: str
    offers: list


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db as test_db
        
        if test_db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = test_db.name if hasattr(test_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = test_db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


# ----- Hotels Endpoints -----

def _ensure_seed_hotels():
    """Seed the database with some demo hotels if empty."""
    if db is None:
        return
    count = db["hotel"].count_documents({})
    if count > 0:
        return
    sample_hotels = [
        {
            "name": "Seaside Vista Resort",
            "location": "Miami Beach, USA",
            "rating": 8.9,
            "reviews": 2312,
            "image": "https://images.unsplash.com/photo-1501117716987-c8e01f2a0a3a?q=80&w=2070&auto=format&fit=crop",
            "offers": [
                {"name": "Booking.com", "price": 182},
                {"name": "Expedia", "price": 176},
                {"name": "Hotels.com", "price": 189},
            ],
        },
        {
            "name": "Alpine Lodge & Spa",
            "location": "Zermatt, Switzerland",
            "rating": 9.2,
            "reviews": 1348,
            "image": "https://images.unsplash.com/photo-1528909514045-2fa4ac7a08ba?q=80&w=2070&auto=format&fit=crop",
            "offers": [
                {"name": "Booking.com", "price": 245},
                {"name": "Expedia", "price": 239},
                {"name": "Hotels.com", "price": 252},
            ],
        },
        {
            "name": "City Center Boutique Hotel",
            "location": "Tokyo, Japan",
            "rating": 8.6,
            "reviews": 5120,
            "image": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?q=80&w=2070&auto=format&fit=crop",
            "offers": [
                {"name": "Booking.com", "price": 128},
                {"name": "Expedia", "price": 119},
                {"name": "Hotels.com", "price": 130},
            ],
        },
        {
            "name": "Lagoon Overwater Villas",
            "location": "Malé, Maldives",
            "rating": 9.5,
            "reviews": 874,
            "image": "https://images.unsplash.com/photo-1519710164239-da123dc03ef4?q=80&w=2070&auto=format&fit=crop",
            "offers": [
                {"name": "Booking.com", "price": 612},
                {"name": "Expedia", "price": 598},
                {"name": "Hotels.com", "price": 629},
            ],
        },
    ]
    for h in sample_hotels:
        create_document("hotel", h)


@app.get("/hotels", response_model=List[HotelResponse])
def list_hotels(
    destination: Optional[str] = Query(None, description="Filter by destination/location substring"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum best-offer price"),
    min_rating: Optional[float] = Query(None, ge=0, le=10, description="Minimum rating"),
    limit: int = Query(20, ge=1, le=100),
):
    _ensure_seed_hotels()

    # Base filter
    f: dict = {}
    if destination:
        f["location"] = {"$regex": destination, "$options": "i"}
    if min_rating is not None:
        f["rating"] = {"$gte": float(min_rating)}

    docs = get_documents("hotel", f, limit=limit)

    # Optionally filter by best price
    hotels = []
    for d in docs:
        offers = d.get("offers", [])
        best_price = min([o.get("price", 0) for o in offers], default=None)
        if max_price is not None and best_price is not None and best_price > max_price:
            continue
        hotels.append({
            "id": str(d.get("_id")),
            "name": d.get("name"),
            "location": d.get("location"),
            "rating": float(d.get("rating", 0)),
            "reviews": int(d.get("reviews", 0)),
            "image": d.get("image"),
            "offers": offers,
        })

    # Basic sorting: recommended by best price asc
    hotels.sort(key=lambda h: min([o["price"] for o in h.get("offers", [])]) if h.get("offers") else 1e9)

    return hotels


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
