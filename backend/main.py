import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ROOT, "ml"))  # so we can import forecast, reorder, analytics
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # so we can import auth

import sqlite3
from datetime import date, datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

import analytics
import auth
import ask
import traceback
import reorder
app = FastAPI(title="Smart Inventory API")
DB = os.path.join(ROOT, "data", "inventory.db")

# Allow the React app (added later) to call this API from the browser
app.add_middleware(
    CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

auth.init_users_table()


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=6, max_length=72)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register")
def register(creds: Credentials):
    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (
                creds.username,
                auth.hash_password(creds.password),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()
    return {"message": "User registered"}


@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    conn = sqlite3.connect(DB)
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?", (form.username,)
    ).fetchone()
    conn.close()
    if row is None or not auth.verify_password(form.password, row[0]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {"access_token": auth.create_token(form.username), "token_type": "bearer"}


@app.get("/auth/me")
def me(user: str = Depends(auth.get_current_user)):
    return {"username": user}


@app.get("/products")
def products(user: str = Depends(auth.get_current_user)):
    conn = sqlite3.connect(DB)
    df = pd.read_sql(
        """
        SELECT p.stock_code, TRIM(p.description) AS description, p.unit_price,
                              COALESCE(SUM(b.quantity), 0) AS stock, p.shelf_life_days, p.category
                FROM products p LEFT JOIN stock_batches b ON b.stock_code = p.stock_code
          AND (b.expiry_date IS NULL OR b.expiry_date >= (SELECT value FROM settings WHERE key = 'as_of_date'))
        GROUP BY p.stock_code ORDER BY p.description
        """,
        conn,
    )
    conn.close()
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict(orient="records")


@app.get("/alerts/expiry")
def expiry(user: str = Depends(auth.get_current_user)):
    return analytics.expiry_alerts(30).to_dict(orient="records")


@app.get("/summary/daily")
def daily(days: int = 7, user: str = Depends(auth.get_current_user)):
    return analytics.daily_summary(days).to_dict(orient="records")

@app.get("/reorder")
def reorder_recommendations(
    only_needed: bool = True, user: str = Depends(auth.get_current_user)
):
    rec = reorder.get_recommendations()
    if only_needed:
        rec = rec[rec["needs_order"]]
    rec = rec.copy()
    rec["description"] = rec["description"].str.strip()
    rec = rec.sort_values("days_of_cover")
    rec = rec.astype(object).where(rec.notna(), None)
    return rec.to_dict(orient="records")


class SaleItem(BaseModel):
    stock_code: str
    quantity: int = Field(gt=0, le=10000)


@app.post("/sales")
def record_sale(item: SaleItem, user: str = Depends(auth.get_current_user)):
    conn = sqlite3.connect(DB)
    try:
        as_of = conn.execute(
            "SELECT value FROM settings WHERE key = 'as_of_date'"
        ).fetchone()[0]
        product = conn.execute(
            "SELECT description, unit_price FROM products WHERE stock_code = ?",
            (item.stock_code,),
        ).fetchone()
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        # Sellable batches: earliest expiry first, no expired stock
        batches = conn.execute(
            """
            SELECT id, quantity FROM stock_batches
            WHERE stock_code = ? AND quantity > 0
              AND (expiry_date IS NULL OR expiry_date >= ?)
            ORDER BY expiry_date IS NULL, expiry_date, received_date
            """,
            (item.stock_code, as_of),
        ).fetchall()
        available = sum(q for _, q in batches)
        if available < item.quantity:
            raise HTTPException(
                status_code=400, detail=f"Not enough stock. Available: {available}"
            )

        remaining = item.quantity
        for batch_id, qty in batches:
            take = min(qty, remaining)
            conn.execute(
                "UPDATE stock_batches SET quantity = quantity - ? WHERE id = ?",
                (take, batch_id),
            )
            remaining -= take
            if remaining == 0:
                break

        now = datetime.now().strftime("%H:%M:%S")
        conn.execute(
            "INSERT INTO sales (invoice, sale_datetime, sale_date, stock_code, quantity, unit_price) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("LIVE", f"{as_of} {now}", as_of, item.stock_code, item.quantity, product[1]),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "message": "Sale recorded",
        "product": product[0].strip(),
        "quantity": item.quantity,
        "total": round(item.quantity * product[1], 2),
        "stock_left": available - item.quantity,
    }

class NewProduct(BaseModel):
    stock_code: str = Field(min_length=2, max_length=30)
    description: str = Field(min_length=2, max_length=80)
    unit_price: float = Field(gt=0, le=1000000)
    category: Optional[str] = Field(default=None, max_length=40)
    shelf_life_days: Optional[int] = Field(default=None, ge=1, le=3650)


@app.post("/products")
def add_product(p: NewProduct, user: str = Depends(auth.get_current_user)):
    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            "INSERT INTO products (stock_code, description, unit_price, shelf_life_days, category) "
            "VALUES (?, ?, ?, ?, ?)",
            (p.stock_code.strip(), p.description.strip(), p.unit_price, p.shelf_life_days, p.category),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="A product with this stock code already exists")
    finally:
        conn.close()
    return {"message": "Product added", "stock_code": p.stock_code.strip()}


class Receive(BaseModel):
    stock_code: str
    quantity: int = Field(gt=0, le=100000)
    cost_price: float = Field(gt=0, le=1000000)
    expiry_date: Optional[date] = None


@app.post("/stock/receive")
def receive_stock(r: Receive, user: str = Depends(auth.get_current_user)):
    conn = sqlite3.connect(DB)
    try:
        as_of = date.fromisoformat(
            conn.execute("SELECT value FROM settings WHERE key = 'as_of_date'").fetchone()[0]
        )
        prod = conn.execute(
            "SELECT description, shelf_life_days FROM products WHERE stock_code = ?", (r.stock_code,)
        ).fetchone()
        if prod is None:
            raise HTTPException(status_code=404, detail="Product not found")
        if prod[1] is not None:
            if r.expiry_date is None:
                raise HTTPException(status_code=400, detail="This is a perishable product. Enter an expiry date.")
            if r.expiry_date <= as_of:
                raise HTTPException(status_code=400, detail="Expiry date must be in the future.")
        elif r.expiry_date is not None:
            raise HTTPException(status_code=400, detail="This product does not expire. Leave the expiry date empty.")

        conn.execute(
            "INSERT INTO stock_batches (stock_code, quantity, received_date, expiry_date, cost_price) "
            "VALUES (?, ?, ?, ?, ?)",
            (r.stock_code, r.quantity, as_of.isoformat(),
             r.expiry_date.isoformat() if r.expiry_date else None, r.cost_price),
        )
        conn.commit()
        total = conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM stock_batches WHERE stock_code = ? "
            "AND (expiry_date IS NULL OR expiry_date >= ?)",
            (r.stock_code, as_of.isoformat()),
        ).fetchone()[0]
    finally:
        conn.close()
    return {"message": "Stock received", "product": prod[0].strip(), "stock": total}

class Question(BaseModel):
    question: str = Field(min_length=3, max_length=300)


@app.post("/ask")
def ask_shop(q: Question, user: str = Depends(auth.get_current_user)):
    try:
        return ask.answer(q.question)
    except ask.AskError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=503, detail="The assistant is unavailable right now. Please try again in a minute.")

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DIST = os.path.join(ROOT, "frontend", "dist")
if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def serve_frontend(path: str):
        file = os.path.realpath(os.path.join(DIST, path))
        if path and file.startswith(os.path.realpath(DIST)) and os.path.isfile(file):
            return FileResponse(file)
        return FileResponse(os.path.join(DIST, "index.html"))