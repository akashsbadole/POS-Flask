from flask import Blueprint

bp = Blueprint('kitchen', __name__)

from . import routes