
from src import app
from waitress import serve

# production server
serve(app, host='0.0.0.0', port=5000)
