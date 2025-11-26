from flask import Blueprint

bp = Blueprint('tables', __name__)

from . import routes