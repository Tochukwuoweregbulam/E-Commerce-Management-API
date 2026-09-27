from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr

from .models import OrderStatus


class UserCreate(BaseModel):
    username: str
    email: str
    password: str = Field(min_length=8, max_length=72)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: int
    email: str
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    price_cents: int = Field(ge=0)
    stock_quantity: int = Field(ge=0)


class ProductPublic(ProductCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str
    phone: str | None = None
    address: str | None = None


class CustomerPublic(CustomerCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class StockAdjustment(BaseModel):
    quantity: int = Field(gt=0)


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemPublic(BaseModel):
    product_id: int
    quantity: int
    unit_price_cents: int
    model_config = ConfigDict(from_attributes=True)


class OrderPublic(BaseModel):
    id: int
    customer_id: int
    status: OrderStatus
    total_cents: int
    created_at: datetime | None
    items: list[OrderItemPublic]
    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class InventoryUpdate(BaseModel):
    product_id: int
    quantity: int