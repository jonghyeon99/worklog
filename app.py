import os
from dotenv import load_dotenv
from flask import Flask
from routes.auth import auth_bp
from routes.main import main_bp

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
