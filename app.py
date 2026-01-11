"""
PageCraft - Flask Website Builder CMS
Main application entry point
"""
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import app factory
from app import create_app

# Create Flask application
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
