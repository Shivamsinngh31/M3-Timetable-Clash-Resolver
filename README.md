# M3 Timetable Clash Resolver

## Project Overview
The M3 Timetable Clash Resolver is an automatic timetable generation and clash detection system developed using Python.

It helps generate academic timetables while checking student, faculty, classroom, and scheduling constraints.

## Features
- Automatic timetable generation
- Student timetable clash detection
- Faculty timetable clash detection
- Classroom double-booking detection
- Classroom capacity validation
- Lunch break validation (1 PM to 2 PM)
- Back-to-back lecture validation
- SQLite database for storing timetable information
- Interactive Streamlit interface

## Technologies Used
- Python
- Streamlit
- SQLite
- Pandas
- Google OR-Tools (if included in the scheduling implementation)

## Project Structure
- `app.py` – Main Streamlit application
- `database.py` – Database creation and demo data
- `scheduler.py` – Timetable scheduling logic
- `requirements.txt` – Project dependencies
- `test_clashes.py` – Clash detection tests
- `test_lunch.py` – Lunch break test
- `test_capacity.py` – Classroom capacity test
- `test_back_to_back.py` – Consecutive lecture test

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Run the Application

```bash
streamlit run app.py
```

## Run Tests

```bash
python test_clashes.py
python test_lunch.py
python test_capacity.py
python test_back_to_back.py
```

## Database
The project uses SQLite to store students, faculty, courses, classrooms, sections, and enrollments.

## Author
Shivam Singh

## Project
M3 Timetable Clash Resolver
