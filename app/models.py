'''
CS3250 - Software Development Methods and Tools - Fall 2023
Instructor: Thyago Mota
Student: 
Description: Project 2 - Queen Soopers Web App
'''

from app import db 
from flask_login import UserMixin


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    customer_id = db.Column(db.String)
    passwd = db.Column(db.String)
    orders = db.relationship("Order", backref="user_orders", foreign_keys="[Order.user_id]")

class Order(db.Model):
    __tablename__ = 'orders'
    date = db.Column(db.String(100), nullable=False)
    upc = db.Column(db.String(100), primary_key=True)
    item = db.Column(db.String(100), nullable=False)
    paid = db.Column(db.Float(100), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('user_orders', lazy=True), foreign_keys="[Order.user_id]")
