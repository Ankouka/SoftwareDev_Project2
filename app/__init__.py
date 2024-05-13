'''
CS3250 - Software Development Methods and Tools - Fall 2023
Instructor: Thyago Mota
Student: 
Description: Project 2 - Queen Soopers Web App
'''

from flask import Flask
import os
import csv

app = Flask("Queen Soopers Web App")
app.secret_key = os.environ['SECRET_KEY']

# db initialization
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db.init_app(app)

from app import models
with app.app_context(): 
    db.create_all()

# login manager
from flask_login import LoginManager
login_manager = LoginManager()
login_manager.init_app(app)

from app.models import User, Order

# user_loader callback
@login_manager.user_loader
def load_user(id):
    try: 
        return db.session.query(User).filter(User.id==id).one()
    except: 
        return None

# read orders from the cvs
def read_orders_from_csv(user):
    with open('data/' + user.id + '_orders.csv', 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            order = Order(date=row['date'], upc=row['upc'], item=row['item'], paid=row['paid'])
            db.session.add(order)
        db.session.commit()
        
# cache setup
from flask_caching import Cache
cache = Cache()
cache.init_app(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

from app import routes
