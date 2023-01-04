# from product import *
from sqlalchemy.dialects import postgresql
from uuid import uuid4
import deps
import auth
from fastapi import FastAPI, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from models import Base
from typing import List, Union
import models as md
from sqlalchemy.orm import Session, joinedload, load_only
from paginate_sqlalchemy import SqlalchemyOrmPage
from pydantic import BaseModel
from sqlalchemy import desc, select, join
from sqlalchemy.orm import Load, subqueryload
from sqlalchemy.exc import IntegrityError
from datetime import date as dt_date
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from db_conn import *
# starlette.routing.Route
from starlette.routing import Route

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.swagger_ui_init_oauth

item_not_foud = {"error": "item not found"}


def returner(p: SqlalchemyOrmPage):
  return {'items': p.items, 'page_count': p.page_count, 'page': p.page, 'next_page': p.next_page}


def check_item_not_found(item):
  if item is None:
    return JSONResponse(item_not_foud, status_code=404)
  return item


def error_response(e):
  # try:
  err: str = e.args.__getitem__(0)
  ind = err.index('DETAIL')
  if ind == -1:
    ind = 0
  raise HTTPException(status_code=400, detail=err[ind:])


def commit_func(db: Session):
  try:
    db.commit()
  except Exception as e:
    return error_response(e)


def get_one(item_id: int, sql_model: Base, db: Session):
  q = db.get(sql_model, item_id)
  return check_item_not_found(q)


def add(pydantic_model: BaseModel, sql_model: Base, db: Session, user_id: int = 0):
  q_data = pydantic_model.dict(exclude_unset=True)
  try:
    for k, v in q_data.items():
      setattr(sql_model, k, v)
    sql_model.id = None
    if user_id != 0:
      sql_model.user_id = user_id
    db.add(sql_model)
    db.commit()
  except Exception as e:
    # print(e)
    db.rollback()
    raise error_response(e)
  return q_data


def update(item: BaseModel, item_id: int, sql_model: Base, db: Session):
  q = db.get(sql_model, item_id)
  if q is None:
    return JSONResponse(item_not_foud, status_code=404)
  q_data = item.dict(exclude_unset=True)
  try:
    for k, v in q_data.items():
      setattr(q, k, v)
    db.add(q)
    db.commit()
    db.refresh(q)
  except Exception as e:
    db.rollback()
    return error_response(e)
  return q


@app.on_event("startup")
def on_startup():
  create_db_and_tables()


@app.post('/api/user', summary="Create new user", response_model=md.PydanticUser)
def create_user(data: md.PydanticUser, db: Session = Depends(get_db)):
    # querying database to check if user already exist
  # user = db.query(md.User).filter(md.User.login == data.login).first()
  # if user is not None:
  #   raise HTTPException(
  #       status_code=status.HTTP_400_BAD_REQUEST,
  #       detail="User with this email already exist"
  #   )
  data.password = auth.get_hashed_password(data.password)
  add(data, md.User(), db)
  return data


@app.post('/api/login', summary="Create access and refresh tokens for user")
def login(item: md.PydanticLogin, db: Session = Depends(get_db)):

  user: md.User = db.query(md.User).filter(
      md.User.login == item.login).first()

  if user is None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Incorrect login or password"
    )

  hashed_pass = user.password
  if not auth.verify_password(item.password, hashed_pass):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Incorrect email or password"
    )

  return {
      "access_token": auth.create_access_token(user.id),
      "refresh_token": auth.create_refresh_token(user.id),
  }


@app.post('/api/login_form', summary="Create access and refresh tokens for user for swagger")
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

  user: md.User = db.query(md.User).filter(
      md.User.login == form_data.username).first()

  if user is None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Incorrect login or password"
    )

  hashed_pass = user.password
  if not auth.verify_password(form_data.password, hashed_pass):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Incorrect email or password"
    )

  return {
      "access_token": auth.create_access_token(user.id),
      "refresh_token": auth.create_refresh_token(user.id),
  }


@app.get('/api/me', summary='Get details of currently logged in user', response_model=md.PydanticUser)
def get_me(user: md.User = Depends(deps.auth_middleware)):
  return user


@app.get('/api/refresh_token', summary='Get details of currently logged in user')
def refresh_token(tokens: dict = Depends(deps.auth_refresh_token)):
  return tokens


@app.get("/api/product/{item_id}")
def get_product(item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return get_one(item_id, md.Product, db)


@app.get("/api/product")
def get_product_all(page: int = 1, page_size: int = 10, name: str = '',
                    user: md.User = Depends(deps.auth_middleware),  db: Session = Depends(get_db)):
  q = db.query(md.Product).order_by(md.Product.name)
  if name != '':
    q = db.query(md.Product).filter(md.Product.name.ilike(f'%{name}%'))
  p = SqlalchemyOrmPage(q, page=page, items_per_page=page_size)
  return returner(p)


@app.post("/api/product", )
def add_product(item: md.PydanticProduct, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return add(item, md.Product(), db, user.id)


@app.put("/api/product/{item_id}")
def update_product(item: md.PydanticProduct, item_id: int, user: md.User = Depends(deps.auth_middleware),  db: Session = Depends(get_db)):
  return update(item=item, item_id=item_id, sql_model=md.Product, db=db)


@app.get("/api/supplier/{item_id}")
def get_supplier(item_id: int, user: md.User = Depends(deps.auth_middleware),  db: Session = Depends(get_db)):
  return get_one(item_id, md.Supplier, db)


@app.get("/api/supplier")
def get_supplier_all(page: int = 1, page_size: int = 10, name: str = '', user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  q = db.query(md.Supplier).order_by(md.Supplier.name)
  if name != '':
    q = db.query(md.Supplier).filter(md.Supplier.name.ilike(f'%{name}%'))
  p = SqlalchemyOrmPage(q, page=page, items_per_page=page_size)
  return returner(p)


@app.put("/api/supplier/{item_id}")
def update_supplier(
        item: md.PydanticSupplier,
        item_id: int,
        user: md.User = Depends(deps.auth_middleware),
        db: Session = Depends(get_db)):
  return update(item=item, item_id=item_id, sql_model=md.Supplier, db=db)


@app.post("/api/supplier")
def add_supplier(item: md.PydanticSupplier, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):

  return add(item, md.Supplier(), db, user.id)


@app.get("/api/unit/{item_id}")
def get_unit(item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return get_one(item_id, md.Unit, db)


@app.get("/api/unit")
def get_unit_all(page: int = 1, page_size: int = 10, name: str = '', user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  q = db.query(md.Unit).order_by(md.Unit.name)
  if name != '':
    q = db.query(md.Unit).filter(md.Unit.name.ilike(f'%{name}%'))
  p = SqlalchemyOrmPage(q, page=page, items_per_page=page_size)
  return returner(p)


@app.put("/api/unit/{item_id}")
def update_unit(item: md.PydanticUnit, item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return update(item=item, item_id=item_id, sql_model=md.Unit, db=db)


@app.post("/api/unit")
def add_unit(item: md.PydanticUnit, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return add(item, md.Unit(), db, user.id)


@app.get("/api/master/{item_id}")
def get_master(item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return get_one(item_id, md.Master, db)


@app.get("/api/master")
def get_master_all(page: int = 1, page_size: int = 10, name: str = '', user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  q = db.query(md.Master).order_by(md.Master.name)
  if name != '':
    q = db.query(md.Master).filter(md.Master.name.ilike(f'%{name}%'))
  p = SqlalchemyOrmPage(q, page=page, items_per_page=page_size)
  return returner(p)


@app.put("/api/master/{item_id}")
def update_master(item: md.PydanticMaster, item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return update(item=item, item_id=item_id, sql_model=md.Master, db=db)


@app.post("/api/master")
def add_master(item: md.PydanticMaster, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return add(item, md.Master(), db, user.id)


@app.get("/api/arrival/{item_id}")
def get_arrival(item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return get_one(item_id, md.Arrival, db)


@app.get("/api/arrival")
def get_arrival_all(page: int = 1, page_size: int = 10,
                    supplier_id: Union[int, None] = None,
                    invoce_number: Union[str, None] = None,
                    info: Union[str, None] = None,
                    from_date: Union[dt_date, None] = None,
                    to_date: Union[dt_date, None] = None,
                    manufacturer: Union[str, None] = None,
                    unit_id: Union[int, None] = None,
                    from_purchase_price: Union[float, None] = None,
                    to_purchase_price: Union[float, None] = None,
                    from_retail_price: Union[float, None] = None,
                    to_retail_price: Union[float, None] = None,
                    product_id: Union[int, None] = None,
                    status: Union[int, None] = None,
                    user: md.User = Depends(deps.auth_middleware),
                    db: Session = Depends(get_db)):
  q = db.query(md.Arrival).order_by(md.Arrival.id.desc())
  if from_date or to_date:
    q = db.query(md.Arrival).filter(
        md.Arrival.date.between(from_date, to_date))
  if invoce_number:
    q = db.query(md.Arrival).filter(
        md.Arrival.invoce_number.ilike(f'%{invoce_number}%'))
  if manufacturer:
    q = db.query(md.Arrival).filter(
        md.Arrival.manufacturer.ilike(f'%{manufacturer}%'))
  if info:
    q = db.query(md.Arrival).filter(md.Arrival.info.ilike(f'%{info}%'))
  if supplier_id:
    q = db.query(md.Arrival).filter(md.Arrival.supplier_id == supplier_id)
  if status:
    q = db.query(md.Arrival).filter(md.Arrival.status in status)
  if unit_id:
    q = db.query(md.Arrival).filter(md.Arrival.unit_id == unit_id)
  if product_id:
    q = db.query(md.Arrival).filter(md.Arrival.product_id == product_id)
  if from_purchase_price or to_purchase_price:
    q = db.query(md.Arrival).filter(md.Arrival.purchase_price >=
                                    from_purchase_price, md.Arrival.purchase_price <= to_purchase_price)
  if from_retail_price or to_retail_price:
    q = db.query(md.Arrival).filter(md.Arrival.retail_price >=
                                    from_retail_price, md.Arrival.retail_price <= to_retail_price)
  q = q.options(
      joinedload(md.Arrival.product).options(
          load_only(md.Product.name)
      ),
      joinedload(md.Arrival.unit).options(
          load_only(md.Unit.name)
      ),
      joinedload(md.Arrival.supplier).options(
          load_only(md.Supplier.name)
      ),
  )
  p = SqlalchemyOrmPage(q, page=page, items_per_page=page_size)
  return returner(p)


@app.put("/api/arrival/{item_id}")
def update_arrival(item: md.PydanticArrival, item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return update(item=item, item_id=item_id, sql_model=md.Arrival, db=db)


def add_arrival_to_stock(item: md.Arrival, db: Session):
  st: md.Stock = db.query(md.Stock).filter(
      md.Stock.product_id == item.product_id,
      md.Stock.supplier_id == item.supplier_id,
      md.Stock.price == item.retail_price
  ) .first()
  if st is not None:
    try:
      st.count += item.count
      db.add(st)
      db.commit()
      db.refresh(st)
      return
    except Exception as e:
      db.rollback()
      raise error_response(e)
  try:
    st = md.Stock()
    st.product_id = item.product_id
    st.supplier_id = item.supplier_id
    st.count = item.count
    st.price = item.retail_price
    st.unit_id = item.unit_id
    db.add(st)
    db.commit()
    return
  except Exception as e:
    db.rollback()
    raise error_response(e)


@app.post("/api/arrival")
def add_arrival(item: md.PydanticArrivalAdd, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  # ar_list = List[md.Arrival]
  for x in item.items:
    ar = md.Arrival()
    ar.manufacturer = x.manufacturer
    ar.product_id = x.product_id
    ar.count = x.count
    ar.unit_id = x.unit_id
    ar.purchase_price = x.purchase_price
    ar.retail_price = x.retail_price
    ar.info = x.info
    ar.invoce_number = item.invoce_number
    ar.supplier_id = item.supplier_id
    ar.user_id = user.id
    db.add(ar)
    add_arrival_to_stock(ar, db)
  try:
    db.commit()
  except Exception as e:
    # print(e.args)
    db.rollback()
    return error_response(e)
  return item


@app.get("/api/sale/{item_id}")
def get_sale(item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return get_one(item_id, md.Sale, db)


@app.get("/api/sale")
def get_sale_all(page: int = 1, page_size: int = 10,
                 from_date: Union[dt_date, None] = None,
                 to_date: Union[dt_date, None] = None,
                 car_vin: Union[str, None] = None,
                 car_number: Union[str, None] = None,
                 master_id: Union[int, None] = None,
                 service: Union[str, None] = None,
                 product_id: Union[int, None] = None,
                 user_id: Union[int, None] = None,
                 from_price: Union[float, None] = None,
                 to_price: Union[float, None] = None,
                 car_model: Union[str, None] = None,
                 user=Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  q = db.query(md.Sale).order_by(md.Sale.id.desc())
  if from_date or to_date:
    q = q.filter(md.Sale.date.between(from_date, to_date))
  if car_vin:
    q = q.filter(md.Sale.car_vin.ilike(f'%{car_vin}%'))
  if service:
    q = q.filter(md.Sale.service.ilike(f'%{service}%'))
  if car_model:
    q = q.filter(md.Sale.car_model.ilike(f'%{car_model}%'))
  if car_number:
    q = q.filter(md.Sale.car_number.ilike(f'%{car_number}%'))
  if master_id:
    q = q.filter(md.Sale.master_id == master_id)
  if product_id:
    q = q.filter(md.Sale.product.any(md.Product.id == product_id))
  if user_id:
    q = q.filter(md.Sale.user_id == user_id)
  if from_price or to_price:
    q = q.filter(md.Sale.price >=
                 from_price, md.Sale.price <= to_price)
  q = q.options(
      joinedload(md.Sale.master).options(
          load_only(md.Master.name)
      ),
      joinedload(md.Sale.product).options(
          load_only(md.Product.name)
      ),
      joinedload(md.Sale.user).options(
          load_only(md.User.login)
      ),
  )
  p = SqlalchemyOrmPage(q, page=page, items_per_page=page_size)
  return returner(p)


@app.put("/api/sale/{item_id}")
def update_sale(item: md.PydanticSale, item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return update(item=item, item_id=item_id, sql_model=md.Sale, db=db)


@app.post("/api/sale")
def add_sale(item: md.PydanticSaleAdd, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  # item.status = 1
  # for i in item.products_id:
  #   item
  sale = md.Sale()
  sale.date = item.date
  sale.car_model = item.car_model
  sale.car_vin = item.car_vin
  sale.master_id = item.master_id
  sale.service = item.service
  sale.price = item.price
  sale.user_id = user.id
  sale.car_number = item.car_number
  prodcts = db.query(md.Product).filter(
      md.Product.id.in_(item.products_id)).all()
  # print(len(prodcts))
  # print(len(item.products_id))
  sale.product.extend(prodcts)
  db.add(sale)
  db.commit()
  return sale


@app.get("/api/product_return/{item_id}")
def get_product_return(item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return get_one(item_id, md.ProductReturn, db)


@app.delete("/api/product_return/{item_id}")
def delete_product_return(item_id: int, user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  pr: md.ProductReturn = db.get(md.ProductReturn, item_id)
  if pr is None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="item not found")
  if pr.status != 0:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="item was spended")
  db.delete(pr)
  db.commit()
  return pr


@app.get("/api/product_return")
def get_product_return_all(page: int = 1, page_size: int = 10,
                           from_date: Union[dt_date, None] = None,
                           to_date: Union[dt_date, None] = None,
                           from_price: Union[float, None] = None,
                           to_price: Union[float, None] = None,
                           supplier_id: Union[int, None] = None,
                           product_id: Union[int, None] = None,
                           status: Union[int, None] = None,
                           user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  # session.query(User).options(
  #                 subqueryload(User.addresses).load_only(Address.email_address)
  #         )
  q = db.query(md.ProductReturn).options(
      subqueryload(md.ProductReturn.product),
      subqueryload(md.ProductReturn.supplier),
      subqueryload(md.ProductReturn.user).load_only(md.User.login),
  ).order_by(md.ProductReturn.id.desc())
  if from_date or to_date:
    q = q.filter(
        md.ProductReturn.date.between(from_date, to_date))
  if supplier_id:
    q = q.filter(
        md.ProductReturn.supplier_id == supplier_id)
  # print(status)
  if status is not None:
    q = q.filter(md.ProductReturn.status == status)
  if product_id:
    q = q.filter(
        md.ProductReturn.product_id == product_id)
  if from_price or to_price:
    q = q.filter(md.ProductReturn.price >=
                 from_price, md.ProductReturn.price <= to_price)
  p = SqlalchemyOrmPage(q, page=page, items_per_page=page_size)
  return returner(p)


@app.put("/api/product_return/{item_id}")
def update_product_return(item: md.PydanticProductReturn, item_id: int,
                          user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return update(item=item, item_id=item_id, sql_model=md.ProductReturn, db=db)


@app.post("/api/product_return")
def add_product_return(item: md.PydanticProductReturn,
                       user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  item.status = 0
  return add(item, md.ProductReturn(), db, user.id)


@app.post("/api/product_return/spend")
def product_return_spend(item_id: int,
                         user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  item: md.ProductReturn = db.get(md.ProductReturn, item_id)
  if item is None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="item not found",
    )
  if item.status == 1:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="item is spended",
    )
  item.status = 1
  stock: md.Stock = db.query(md.Stock).filter(
      md.Stock.price == item.price, md.Stock.product_id == item.product_id, md.Stock.supplier_id == item.supplier_id).first()
  if stock is None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Stock item not found",
    )
  if stock.count < item.count:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="product count is not valid",
    )
  stock.count -= item.count
  try:
    db.add(stock)
    db.commit()
    db.refresh(stock)
  except Exception as e:
    db.rollback()
    return error_response(e)
  try:
    db.add(item)
    db.commit()
    db.refresh(item)
  except Exception as e:
    db.rollback()
    return error_response(e)
  return item


@app.get("/api/disposal/{item_id}")
def get_disposal(item_id: int,
                 user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return get_one(item_id, md.Disposal, db)


@app.get("/api/disposal")
def get_disposal_all(page: int = 1, page_size: int = 10,
                     from_date: Union[dt_date, None] = None,
                     to_date: Union[dt_date, None] = None,
                     product_id: Union[int, None] = None,
                     cause: Union[str, None] = None,
                     user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  q = db.query(md.Disposal).options(
      subqueryload(md.Disposal.product).load_only(md.Product.name),
      subqueryload(md.Disposal.user).load_only(md.User.login)
  ).order_by(desc(md.Disposal.id))
  if from_date or to_date:
    q = q.filter(
        md.Disposal.date.between(from_date, to_date))
  if product_id:
    q = q.filter(md.Disposal.product_id == product_id)
  if cause:
    q = q.filter(md.Disposal.cause.ilike(f'%{cause}%'))
  p = SqlalchemyOrmPage(q, page=page, items_per_page=page_size)
  return returner(p)


@app.put("/api/disposal/{item_id}")
def update_disposal(item: md.PydanticDisposal, item_id: int,
                    user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return update(item=item, item_id=item_id, sql_model=md.Disposal, db=db)


@app.post("/api/disposal")
def add_disposal(item: md.PydanticDisposal,
                 user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  # # item.status = 1
  return add(item, md.Disposal(), db, user.id)


@app.get("/api/inventory/{item_id}")
def get_inventory(item_id: int,
                  user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return get_one(item_id, md.Inventory, db)


@app.get("/api/inventory")
def get_inventory_all(page: int = 1, page_size: int = 10,
                      from_date: Union[dt_date, None] = None,
                      to_date: Union[dt_date, None] = None,
                      inventory_cause: Union[str, None] = None,
                      info: Union[str, None] = None,
                      user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  q = db.query(md.Inventory).options(
      subqueryload(md.Inventory.user).load_only(md.User.login)
  ).order_by(desc(md.Inventory.id))
  if inventory_cause:
    q = db.query(md.Inventory).filter(
        md.Inventory.inventory_cause.ilike(f'%{inventory_cause}%'))
  if info:
    q = db.query(md.Inventory).filter(
        md.Inventory.info.ilike(f'%{info}%'))
  if from_date or to_date:
    q = db.query(md.Inventory).filter(
        md.Inventory.date.between(from_date, to_date))
  p = SqlalchemyOrmPage(q, page=page, items_per_page=page_size)
  return returner(p)


@app.put("/api/inventory/{item_id}")
def update_inventory(item: md.PydanticInventory, item_id: int,
                     user: md.User = Depends(deps.auth_middleware), db: Session = Depends(get_db)):
  return update(item=item, item_id=item_id, sql_model=md.Inventory, db=db)


@app.post("/api/inventory")
def add_inventory(item: md.PydanticInventory,
                  user: md.User = Depends(deps.auth_middleware),
                  db: Session = Depends(get_db)):
  # item.status = 1
  return add(item, md.Inventory(), db, user.id)


@app.get("/api/stock")
def get_stock(page: int = 1, page_size: int = 10,
              supplier_id: Union[int, None] = None,
              product_id: Union[int, None] = None,
              product_name: Union[str, None] = None,
              supplier_name: Union[str, None] = None,
              user: md.User = Depends(deps.auth_middleware),
              db: Session = Depends(get_db)):
  q = db.query(md.Stock).options(
      subqueryload(md.Stock.product).load_only(md.Product.name),
      subqueryload(md.Stock.supplier).load_only(md.Supplier.name),
  ).filter(md.Stock.count > 0).order_by(md.Stock.id.desc())
  if product_id:
    q = q.filter(md.Stock.product_id == product_id)
  if supplier_id:
    q = q.filter(md.Stock.supplier_id == supplier_id)
  if product_name:
    q = q.filter(md.Product.name.ilike(f'%{product_name}%'))
  if supplier_name:
    q = q.filter(md.Supplier.name.ilike(f'%{supplier_name}%'))
  p = SqlalchemyOrmPage(q, page=page, items_per_page=page_size)
  return returner(p)
# rt = Route()
# rt.


# for x in app.routes[4:5]:
#   print(x.path, x.methods)
#   print(x.__dict__)
#   print(type(x.methods))
#   print(type(x))
