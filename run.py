# This is the entry point for the app
# Run this file to start the web server

from app import create_app

# Create the Flask app using the factory function in __init__.py
app = create_app()

# This makes Flask reload templates automatically when they change
# Useful during development so you do not have to restart the server
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Start the app in debug mode when running directly
# Debug mode shows detailed error pages and auto-reloads on code changes
if __name__ == "__main__":
    app.run(debug=True)
