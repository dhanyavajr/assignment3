from flask import Flask, redirect, request, url_for
from flask import Response

import requests

from flask import request
from flask import Flask, render_template

from jinja2 import Template
import secrets

import base64
import json
import os


from flask import session


app = Flask(__name__)

app.secret_key = secrets.token_hex() 


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, ForeignKey, String

from logging.config import dictConfig


dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    },
     'file.handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'weatherportal.log',
            'maxBytes': 10000000,
            'backupCount': 5,
            'level': 'DEBUG',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file.handler']
    }
})

# Not required for assignment3
in_mem_cities = []
in_mem_user_cities = {}


# SQLite Database creation
Base = declarative_base()
engine = create_engine("sqlite:///weatherportal.db", echo=True, future=True)
DBSession = sessionmaker(bind=engine)


@app.before_first_request
def create_tables():
    Base.metadata.create_all(engine)


class Admin(Base):
    __tablename__ = 'admin'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    password = Column(String)

    def __repr__(self):
        return "<Admin(name='%s')>" % (self.name)

    # Ref: https://stackoverflow.com/questions/5022066/how-to-serialize-sqlalchemy-result-to-json
    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields
# myedits 1
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    password = Column(String)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "password": self.password}


class City(Base):
    __tablename__ = 'cities'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    url = Column(String)
    adminid = Column(Integer)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "adminid": self.adminid
        }


class UserCity(Base):
    __tablename__ = 'usercities'
    id = Column(Integer, primary_key=True, autoincrement=True)
    cityId = Column(Integer)
    userId = Column(Integer)
    month = Column(String)
    year = Column(String)
    weather_params = Column(String)

    def as_dict(self):
        return {
            "id": self.id,
            "cityId": self.cityId,
            "userId": self.userId,
            "month": self.month,
            "year": self.year,
            "weather_params": self.weather_params
        }

## Admin REST API
@app.route("/admin", methods=['POST'])
def add_admin():
    app.logger.info("Inside add_admin")
    data = request.json
    app.logger.info("Received request:%s", str(data))

    name = data['name']
    password = data['password']

    admin = Admin(name=name, password=password)

    session = DBSession()
    session.add(admin)
    session.commit()

    return admin.as_dict()


@app.route("/admin")
def get_admins():
    app.logger.info("Inside get_admins")
    ret_obj = {}

    session = DBSession()
    admins = session.query(Admin)
    admin_list = []
    for admin in admins:
        admin_list.append(admin.as_dict())

    ret_obj['admins'] = admin_list
    return ret_obj


@app.route("/admin/<id>")
def get_admin_by_id(id):
    app.logger.info("Inside get_admin_by_id %s\n", id)

    session = DBSession()
    admin = session.get(Admin, id)

    app.logger.info("Found admin:%s\n", str(admin))
    if admin == None:
        status = ("Admin with id {id} not found\n").format(id=id)
        return Response(status, status=404)
    else:
        return admin.as_dict()


@app.route("/admin/<id>", methods=['DELETE'])
def delete_admin_by_id(id):
    app.logger.info("Inside delete_admin_by_id %s\n", id)

    session = DBSession()
    admin = session.query(Admin).filter_by(id=id).first()

    app.logger.info("Found admin:%s\n", str(admin))
    if admin == None:
        status = ("Admin with id {id} not found.\n").format(id=id)
        return Response(status, status=404)
    else:
        session.delete(admin)
        session.commit()
        status = ("Admin with id {id} deleted.\n").format(id=id)
        return Response(status, status=200)

## my USER REST API edits

@app.route("/users", methods=['POST'])
def add_user():

    data = request.json
    name = data['name']
    password = data['password']

    session = DBSession()

    existing_user = session.query(User).filter_by(name=name).first()

    if existing_user:
        return Response("User already exists\n", status=400)

    user = User(name=name, password=password)

    session.add(user)
    session.commit()

    return user.as_dict()


@app.route("/users")
def get_users():

    session = DBSession()

    users = session.query(User)

    user_list = []

    for user in users:
        user_list.append(user.as_dict())

    return {"users": user_list}


@app.route("/users/<id>")
def get_user_by_id(id):

    session = DBSession()

    user = session.get(User, id)

    if user == None:
        return Response("User not found\n", status=404)

    return user.as_dict()


@app.route("/users/<id>", methods=['DELETE'])
def delete_user(id):

    session = DBSession()

    user = session.query(User).filter_by(id=id).first()

    if user == None:
        return Response("User not found\n", status=404)

    session.delete(user)
    session.commit()

    return Response(f"User with id {id} deleted\n", status=200)


@app.route("/logout",methods=['GET'])
def logout():
    app.logger.info("Logout called.")
    session.pop('username', None)
    app.logger.info("Before returning...")
    return render_template('index.html')


@app.route("/login", methods=['POST'])
def login():
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    app.logger.info("Username:%s", username)
    app.logger.info("Password:%s", password)

    session['username'] = username

    my_cities = []
    if username in in_mem_user_cities:
        my_cities = in_mem_user_cities[username]
    return render_template('welcome.html',
            welcome_message = "Personal Weather Portal",
            cities=my_cities,
            name=username,
            addButton_style="display:none;",
            addCityForm_style="display:none;",
            regButton_style="display:inline;",
            regForm_style="display:inline;",
            status_style="display:none;")


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/adminlogin", methods=['POST'])
def adminlogin():
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    app.logger.info("Username:%s", username)
    app.logger.info("Password:%s", password)

    session['username'] = username

    user_cities = in_mem_cities
    return render_template('welcome.html',
            welcome_message = "Personal Weather Portal - Admin Panel",
            cities=user_cities,
            name=username,
            addButton_style="display:inline;",
            addCityForm_style="display:inline;",
            regButton_style="display:none;",
            regForm_style="display:none;",
            status_style="display:none;")


@app.route("/admin")
def adminindex():
    return render_template('adminindex.html')


if __name__ == "__main__":
    app.debug = True  # turn on debug
    app.logger.info('Portal started...')
    app.run(host='0.0.0.0', port=5009) 
