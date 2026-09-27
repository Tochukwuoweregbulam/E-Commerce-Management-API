from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .auth import create_access_token, get_current_user, hash_password, verify_password
from .database import Base, engine, get_db
from .models import Customer, Order, OrderItem, OrderStatus, Product, User
from .schemas import (
    CustomerCreate, CustomerPublic, OrderCreate, OrderPublic, OrderStatusUpdate,
    ProductCreate, ProductPublic, StockAdjustment, Token, UserCreate, UserPublic, LoginRequest, InventoryUpdate
)

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Secure Inventory & Order Management API", version="1.0.0")


def commit_or_conflict(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A record with that unique value already exists")


@app.get("/", tags=["health"])
def health():
    return {"service": "inventory-api", "status": "ok", "docs": "/docs"}


@app.post("/auth/register", response_model=UserPublic, status_code=201, tags=["authentication"])
def register(payload: UserCreate, db: Session = Depends(get_db)):
    user = User(username=payload.username.lower() ,email=payload.email.lower(), hashed_password=hash_password(payload.password))
    db.add(user)
    commit_or_conflict(db)
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token, tags=["authentication"])
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.scalar(
        select(User).where(User.email == data.email.lower())
    )

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer"
    }


@app.get("/products", response_model=list[ProductPublic], tags=["products"])
def list_products(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Product).order_by(Product.id)).all()


@app.post("/products", response_model=ProductPublic, status_code=201, tags=["products"])
def create_product(payload: ProductCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/products/{product_id}", response_model=ProductPublic, tags=["products"])
def get_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@app.put("/products/{product_id}", response_model=ProductPublic, tags=["products"])
def update_product(product_id: int, payload: ProductCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    for key, value in payload.model_dump().items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@app.delete("/products/{product_id}", status_code=204, tags=["products"])
def delete_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    db.delete(product)
    db.commit()

@app.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):

    products = db.scalars(select(Product)).all()

    inventory = []

    for product in products:

        total_sales = db.scalar(
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .where(OrderItem.product_id == product.id)
        )

        inventory.append({
            "product_name": product.name,
            "stock_quantity": product.stock_quantity,
            "sales": total_sales
        })

    return inventory

@app.post("/inventory")
def add_inventory(
    data: InventoryUpdate,
    db: Session = Depends(get_db)
):
    product = db.get(Product, data.product_id)

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if data.quantity <= 0:
          raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0"
        )

    product.stock_quantity += data.quantity

    db.commit()
    db.refresh(product)

    return {
        "product_name": product.name,
        "quantity_added": data.quantity,
        "stock_quantity": product.stock_quantity
    }


@app.post("/customers", response_model=CustomerPublic, status_code=201, tags=["customers"])
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    commit_or_conflict(db)
    db.refresh(customer)
    return customer


@app.get("/customers", response_model=list[CustomerPublic], tags=["customers"])
def list_customers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Customer).order_by(Customer.id)).all()


@app.get("/customers/{customer_id}", response_model=CustomerPublic, tags=["customers"])
def get_customer(customer_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    return customer


@app.post("/orders", response_model=OrderPublic, status_code=201, tags=["orders"])
def create_order(payload: OrderCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.get(Customer, payload.customer_id):
        raise HTTPException(404, "Customer not found")
    product_ids = [item.product_id for item in payload.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(400, "Each product may appear only once per order")
    products = {product.id: product for product in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()}
    if len(products) != len(product_ids):
        raise HTTPException(404, "One or more products not found")
    for item in payload.items:
        if products[item.product_id].stock_quantity < item.quantity:
            raise HTTPException(409, f"Insufficient stock for product {item.product_id}")
    order = Order(customer_id=payload.customer_id, status=OrderStatus.pending, total_cents=0)
    for item in payload.items:
        product = products[item.product_id]
        product.stock_quantity -= item.quantity
        order.items.append(OrderItem(product_id=product.id, quantity=item.quantity, unit_price_cents=product.price_cents))
        order.total_cents += product.price_cents * item.quantity
    db.add(order)
    db.commit()
    db.refresh(order)
    return db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order.id))


@app.get("/orders", response_model=list[OrderPublic], tags=["orders"])
def list_orders(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Order).options(selectinload(Order.items)).order_by(Order.id)).unique().all()


@app.patch("/orders/{order_id}/status", response_model=OrderPublic, tags=["orders"])
def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
    if not order:
        raise HTTPException(404, "Order not found")
    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order


@app.get("/external/exchange-rate", tags=["external integration"])
async def exchange_rate(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get("https://open.er-api.com/v6/latest/NGN")
            response.raise_for_status()
            data = response.json()
        return {"base": data["base_code"], "rates": {"EUR": data["rates"]["EUR"], "GBP": data["rates"]["GBP"], "USD": data["rates"]["USD"]}, "provider": "open.er-api.com"}
    except (httpx.HTTPError, KeyError):
        raise HTTPException(502, "Exchange-rate provider unavailable")
