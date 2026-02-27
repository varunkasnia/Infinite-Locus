from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO()
bcrypt = Bcrypt()
migrate = Migrate()
scheduler = BackgroundScheduler()
