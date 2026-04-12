from app import create_app

app = create_app()

# 🔥 ADD THIS LINE
app.config['TEMPLATES_AUTO_RELOAD'] = True

if __name__ == "__main__":
    app.run(debug=True)