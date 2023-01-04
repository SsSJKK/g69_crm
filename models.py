from email.policy import default
from enum import unique
from xmlrpc.client import Boolean
from sqlalchemy import func
from db_conn import Base

from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey, \
    Float, CheckConstraint,  Date, UniqueConstraint, ARRAY, Table, Boolean
from pydantic_sqlalchemy import sqlalchemy_to_pydantic
from pydantic import BaseModel, Field
from typing import Union, List
from datetime import date as dt_type


class User(Base):
  __tablename__ = "users"
  id = Column(Integer, primary_key=True, index=True)
  login = Column(String(50), unique=True)
  first_name = Column(String(50))
  middle_name = Column(String(50))
  last_name = Column(String(50))
  password = Column(String(300))
  email = Column(String(50), unique=True)
  deleted = Column(Boolean, nullable=False, default=False)
  product = relationship("Product", back_populates="user")
  supplier = relationship("Supplier", back_populates="user")
  unit = relationship("Unit", back_populates="user")
  master = relationship("Master", back_populates="user")
  arrival = relationship("Arrival", back_populates="user")
  sale = relationship("Sale", back_populates="user")
  product_return = relationship("ProductReturn", back_populates="user")
  disposal = relationship("Disposal", back_populates="user")
  inventory = relationship("Inventory", back_populates="user")


sale_product_relationship = Table(
    "sale_product_relationship",
    Base.metadata,
    Column("sale_id", ForeignKey("sales.id"), primary_key=True),
    Column("stock_id", ForeignKey("stock.id"), primary_key=True),
)


class Supplier(Base):
  __tablename__ = "suppliers"
  id = Column(Integer, primary_key=True, index=True)
  name = Column(String)
  arrival = relationship("Arrival", back_populates="supplier")
  stock = relationship("Stock", back_populates="supplier")
  product_return = relationship("ProductReturn", back_populates="supplier")
  user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
  user = relationship("User", back_populates="supplier")


class Unit(Base):
  __tablename__ = "units"
  id = Column(Integer, primary_key=True, index=True)
  name = Column(String)
  arrival = relationship("Arrival", back_populates="unit")
  user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
  user = relationship("User", back_populates="unit")
  stock = relationship("Stock", back_populates="unit")


class Master(Base):
  __tablename__ = "masters"
  id = Column(Integer, primary_key=True, index=True)
  name = Column(String)
  amount = Column(Float, CheckConstraint("amount >=0"), nullable=False, default=0)
  percentage = Column(Float, CheckConstraint("percentage >=0"), nullable=False, default=0)
  sale = relationship("Sale", back_populates="master")
  user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
  user = relationship("User", back_populates="master")


class Arrival(Base):
  __tablename__ = "arrivals"
  id = Column(Integer, primary_key=True, index=True)
  supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
  supplier = relationship("Supplier", back_populates="arrival")
  invoce_number = Column(String, nullable=False, index=True)
  date = Column(Date, nullable=False, server_default=func.now())
  manufacturer = Column(String, nullable=False)
  product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
  product = relationship("Product", back_populates="arrival")
  count = Column(Float, CheckConstraint("count >=0"), nullable=False)
  unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
  unit = relationship("Unit", back_populates="arrival")
  purchase_price = Column(Float, CheckConstraint(
      "purchase_price >=0"), nullable=False)
  retail_price = Column(Float, CheckConstraint(
      "retail_price >=0"), nullable=False)
  info = Column(String, nullable=False)
  status = Column(Integer, CheckConstraint(
      "status in (0,1,2,3)"), default=1, nullable=False)
  user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
  user = relationship("User", back_populates="arrival")


class Sale(Base):
  __tablename__ = "sales"
  id = Column(Integer, primary_key=True, index=True)
  date = Column(Date, nullable=False, server_default=func.now())
  car_model = Column(String, nullable=False)
  car_vin = Column(String, nullable=False)
  master_id = Column(Integer, ForeignKey("masters.id"))
  service = Column(String)
  price = Column(Float, CheckConstraint("price >=0"), nullable=False)
  user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
  car_number = Column(String(10))
  # product_id = Column(Integer, ForeignKey("products.id"))
  # product = relationship("Product", back_populates="sale")
  stock = relationship(
      "Stock", secondary=sale_product_relationship, back_populates="sale"
  )
  master = relationship("Master", back_populates="sale")
  user = relationship("User", back_populates="sale")


class Product(Base):
  __tablename__ = "products"
  id = Column(Integer, primary_key=True, index=True)
  name = Column(String)
  user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
  user = relationship("User", back_populates="product")
  arrival = relationship("Arrival", back_populates="product")
  # sale = relationship("Sale", back_populates="product")
  product_return = relationship("ProductReturn", back_populates="product")
  disposal = relationship("Disposal", back_populates="product")

  stock = relationship("Stock", back_populates="product")


class ProductReturn(Base):
  __tablename__ = "product_returns"
  id = Column(Integer, primary_key=True, index=True)
  date = Column(Date, nullable=False, server_default=func.now())
  supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
  supplier = relationship("Supplier", back_populates="product_return")
  product_id = Column(Integer, ForeignKey("products.id"))
  count = Column(Float, CheckConstraint("count >=0"), nullable=False)
  product = relationship("Product", back_populates="product_return")
  invoce_number = Column(String, nullable=False, index=True)
  price = Column(Float, CheckConstraint("price >=0"), nullable=False)
  status = Column(Integer, CheckConstraint("status in (0,1)"), default=0)
  user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
  user = relationship("User", back_populates="product_return")


class Disposal(Base):
  __tablename__ = "disposals"
  id = Column(Integer, primary_key=True, index=True)
  date = Column(Date, nullable=False, server_default=func.now())
  product_id = Column(Integer, ForeignKey("products.id"))
  product = relationship("Product", back_populates="disposal")
  count = Column(Float, CheckConstraint("count >=0"), nullable=False)
  cause = Column(String, nullable=False)
  user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
  user = relationship("User", back_populates="disposal")


class Inventory(Base):
  __tablename__ = "inventoryes"
  id = Column(Integer, primary_key=True, index=True)
  date = Column(Date, nullable=False, server_default=func.now())
  inventory_cause = Column(String, nullable=False)
  info = Column(String, nullable=False)
  user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
  user = relationship("User", back_populates="inventory")
  status = Column(Integer, CheckConstraint(
      "status in (0,1)"), default=0, nullable=False)


class Stock(Base):
  __tablename__ = "stock"
  id = Column(Integer, primary_key=True, index=True)
  product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
  product = relationship(Product, back_populates="stock")
  supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
  supplier = relationship(Supplier, back_populates="stock")
  count = Column(Float, CheckConstraint("count >=0"), nullable=False)
  price = Column(Float, CheckConstraint("price >=0"), nullable=False)
  unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
  unit = relationship("Unit", back_populates="stock")
  sale = relationship(
      "Sale", secondary=sale_product_relationship, back_populates="stock"
  )


class PydanticArrivalList(BaseModel):
  manufacturer: str
  product_id: int
  count: float
  unit_id: int
  purchase_price: float
  retail_price: float
  info: Union[str, None] = None


class PydanticLogin(BaseModel):
  login: str
  password: str


class PydanticArrivalAdd(BaseModel):
  supplier_id: int
  invoce_number: str
  date: dt_type
  items: List[PydanticArrivalList]


class TokenPayload(BaseModel):
  exp: int
  user_id: int
  token_type: str


class UserAuth(BaseModel):
  login: str = Field(..., description="user login")
  password: str = Field(..., min_length=5, max_length=24,
                        description="user password")


PydanticProduct = sqlalchemy_to_pydantic(Product, exclude=['user_id'])
PydanticSupplier = sqlalchemy_to_pydantic(Supplier, exclude=['user_id'])
PydanticUnit = sqlalchemy_to_pydantic(Unit, exclude=['user_id'])
PydanticMaster = sqlalchemy_to_pydantic(Master, exclude=['user_id'])
PydanticArrival = sqlalchemy_to_pydantic(Arrival, exclude=['user_id'])
PydanticSale = sqlalchemy_to_pydantic(Sale, exclude=['user_id'])
PydanticProductReturn = sqlalchemy_to_pydantic(
    ProductReturn, exclude=['user_id'])
PydanticDisposal = sqlalchemy_to_pydantic(Disposal, exclude=['user_id'])
PydanticInventory = sqlalchemy_to_pydantic(Inventory, exclude=['user_id'])
PydanticUser = sqlalchemy_to_pydantic(User)
PydanticStock = sqlalchemy_to_pydantic(Stock)

class StockList(PydanticSale):
  id : int
  count: float
  price: float


class PydanticSaleAdd(PydanticSale):
  products_id: List[StockList]
