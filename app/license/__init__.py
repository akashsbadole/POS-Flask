from flask import Blueprint

bp = Blueprint('license', __name__)

from app.license import routes