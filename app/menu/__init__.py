from flask import Blueprint

bp = Blueprint('menu', __name__)

from . import routes