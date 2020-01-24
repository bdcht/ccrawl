from flask import g,request,make_response,redirect,url_for,render_template
from flask_restful import Resource

from ccrawl.srv.main import app,mongo,api
from ccrawl.srv.models import *
from ccrawl.srv.forms import *

@app.route('/')
def mainpage():
    return render_template('base.html')
