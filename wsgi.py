import sys
from pathlib import Path

# Add the directory containing your app to the sys.path
app_dir = Path(__file__).resolve().parent
sys.path.append(str(app_dir))

# Import your Flask application
from app import app as application  # assuming your Flask app instance is named 'app'

# Define the WSGI callable (application)
def create_app():
    return application

# Optional: Configure the WSGI server (e.g., Gunicorn)
# Make sure to install Gunicorn first: pip install gunicorn
if __name__ == '__main__':
    from gunicorn.app.base import Application

    class FlaskApp(Application):
        def init(self, parser, opts, args):
            return {
                'bind': '0.0.0.0:5000',  # Set the host and port
                'workers': 4,             # Number of worker processes
            }

        def load(self):
            return create_app()

    # Run the Gunicorn server
    FlaskApp().run()
