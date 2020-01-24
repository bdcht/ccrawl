from flask import Flask
from flask_restful import Api
from flask_pymongo import PyMongo

from ccrawl import conf

app = Flask(__name__)
app.config.from_object(conf.config.Database)
app.config['MONGO_URI'] = conf.config.Database.url

mongo = PyMongo(app)
api = Api(app)

from ccrawl.srv import models
from ccrawl.srv import views

def run():
    app.run()
