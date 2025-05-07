from flask import Flask
from models import db
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return 'Database initialized!'

if __name__ == '__main__':
    app.run(debug=True)
