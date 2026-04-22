# InsightKPI – KPI Tracking Web Application

InsightKPI is a web-based KPI tracking system built using Flask. It allows users to create, manage, and analyse Key Performance Indicators through a simple and interactive dashboard. Users can add KPI data, track performance over time, and export results for further analysis.

Created for academic purposes by Hamid Miakheil at the University of Westminster.

## Technologies Used

* Python (Flask)
* SQLAlchemy
* SQLite
* HTML
* CSS
* JavaScript
* Chart.js
* ReportLab

## Features

* User registration and login system
* Admin account access
* Add, edit, and delete KPI entries
* KPI dashboard with visual charts
* KPI comparison features
* KPI status evaluation (Green / Amber / Red)
* Data filtering by KPI and date
* Export KPI data to PDF and CSV
* Secure authentication system

## Admin Access

An admin account is available for testing the admin functionality of the system.

Email: [hamidmiakheil@gmail.com](mailto:hamidmiakheil@gmail.com)
Password: hamid123

---

# Running the Project Locally in VS Code

## 1. Open the project in VS Code

Open the InsightKPI project folder inside VS Code.

## 2. Create a virtual environment

Open the VS Code terminal and run:

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

## 3. Install dependencies

Run:

```bash
pip install -r requirements.txt
```

## 4. Run the application

Run:

```bash
python3 run.py
```

## 5. Open the website

Open your browser and go to:

```text
http://127.0.0.1:5000
```

---

# Deploying and Running on PythonAnywhere

## 1. Upload or clone the project

Open a Bash console on PythonAnywhere and run:

```bash
git clone <your-github-repository-link>
cd insightkpi
```

## 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure the WSGI file

Open the WSGI configuration file in PythonAnywhere and replace the contents with:

```python
import sys

project_home = '/home/yourusername/insightkpi'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

from run import app as application
```

## 5. Reload the web app

After saving the WSGI file, reload the web application from the PythonAnywhere dashboard.

## 6. Open the deployed website

Visit your PythonAnywhere web app URL.

---

# Notes

* The database (`kpi.db`) will be created automatically inside the `instance` folder
* Ensure all dependencies are installed before running the application
* Make sure the virtual environment is activated before running the application
* If changes do not appear on PythonAnywhere, reload the web app from the dashboard

## Project Purpose

This project was developed as part of a university coursework project focused on building a practical business KPI management system using modern web development technologies.
