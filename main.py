import os
from app import app

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug, port=5001)
