E-Commerce API

A backend REST API built with FastAPI, SQLAlchemy, and SQLite for managing users, products, inventory, customers, and orders.

The project demonstrates authentication, authorization, CRUD operations, stock management, order processing, password hashing, JWT authentication, and integration with an external exchange-rate API.

Technologies Used
Python
FastAPI
SQLAlchemy
SQLite
Pydantic
JWT Authentication
Argon2 Password Hashing
HTTPX
Postman
Features
Authentication
User registration
User login
Password hashing
JWT authentication
Protected endpoints
Products
Create products
View products
Update products
Delete products
Inventory
Add stock to a product
View current stock
View product sales
Stock is reduced when an order is successfully created
Customers
Create customers
View customers
Update customers
Delete customers
Orders
Create orders
View orders
Update order status
Validate product availability
Automatically reduce stock when an order is created
Calculate order information from order items
External API Integration

The API integrates with open.er-api.com to retrieve currency exchange rates.

Nigerian Naira (NGN) is used as the base currency.

Example:

NGN → USD
NGN → EUR
NGN → GBP
Project Structure
E_COMMERCE_API/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   └── ...
│
├── .env
├── .gitignore
├── requirements.txt
├── README.md
└── ecommerce.db

The exact structure may vary depending on how the project is organized.

Installation
1. Clone the Repository
git clone <repository-url>
cd E_COMMERCE_API
2. Create a Virtual Environment
python -m venv .venv
3. Activate the Virtual Environment
Windows
.venv\Scripts\activate
4. Install Dependencies
pip install -r requirements.txt
5. Run the API
uvicorn app.main:app --reload

The API will normally be available at:

http://127.0.0.1:8000

Swagger documentation:

http://127.0.0.1:8000/docs
Authentication

The API uses JWT bearer authentication.

A user must register and log in before accessing protected endpoints.

Registration
POST /auth/register

Example request:

{
    "username": "tochukwu",
    "email": "tochukwu@example.com",
    "password": "password123"
}
Login
POST /auth/login

Example request:

{
    "email": "tochukwu@example.com",
    "password": "password123"
}

Example response:

{
    "access_token": "your-jwt-token",
    "token_type": "bearer"
}

The token is required for protected endpoints.

In Postman, add:

Authorization: Bearer <access_token>
