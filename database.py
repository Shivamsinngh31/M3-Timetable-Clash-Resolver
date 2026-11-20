
import sqlite3

DB_NAME = "timetable.db"


def connect():
    return sqlite3.connect(DB_NAME)


def create_tables():

    con = connect()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            semester INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS faculty (
            faculty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            course_id TEXT PRIMARY KEY,
            course_name TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id TEXT PRIMARY KEY,
            room_name TEXT,
            capacity INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            section_id TEXT PRIMARY KEY,
            course_id TEXT,
            faculty_id TEXT,
            room_id TEXT,
            day TEXT,
            start_time TEXT,
            end_time TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            student_id TEXT,
            section_id TEXT,
            PRIMARY KEY (student_id, section_id)
        )
    """)

    con.commit()
    con.close()


def load_demo_data():

    create_tables()

    con = connect()
    cur = con.cursor()

    # Clear old test data
    for table in [
        "enrollments", "sections", "students",
        "faculty", "courses", "rooms"
    ]:
        cur.execute(f"DELETE FROM {table}")

    first_names = [
        "Aarav", "Vivaan", "Aditya", "Arjun",
        "Reyansh", "Ishaan", "Kabir", "Rohan",
        "Rahul", "Amit", "Priya", "Ananya",
        "Diya", "Isha", "Meera", "Sneha",
        "Neha", "Pooja", "Kavya", "Riya"
    ]

    last_names = [
        "Sharma", "Singh", "Kumar", "Verma",
        "Gupta", "Patel", "Yadav", "Malhotra",
        "Jain", "Das"
    ]

    # 1,500 students
    for i in range(1, 1501):

        first = first_names[(i - 1) % len(first_names)]
        last = last_names[(i - 1) % len(last_names)]

        cur.execute("""
            INSERT INTO students VALUES (?, ?, ?)
        """, (
            f"STU{i:04d}",
            f"{first} {last}",
            2 + (i % 5)
        ))

    # 20 faculty members
    for i in range(1, 21):

        cur.execute("""
            INSERT INTO faculty VALUES (?, ?)
        """, (
            f"FAC{i:03d}",
            f"Professor {i}"
        ))

    # 120 courses
    for i in range(1, 121):

        cur.execute("""
            INSERT INTO courses VALUES (?, ?)
        """, (
            f"CSE{i:03d}",
            f"Computer Science Course {i}"
        ))

    # 20 classrooms, each with capacity 60
    for i in range(1, 21):

        cur.execute("""
            INSERT INTO rooms VALUES (?, ?, ?)
        """, (
            f"ROOM{i:02d}",
            f"Classroom {i}",
            60
        ))

    # 120 sections
    for i in range(1, 121):

        faculty_id = f"FAC{((i - 1) % 20) + 1:03d}"
        room_id = f"ROOM{((i - 1) % 20) + 1:02d}"

        cur.execute("""
            INSERT INTO sections
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f"SEC{i:03d}",
            f"CSE{i:03d}",
            faculty_id,
            room_id,
            "Monday",
            "09:00",
            "10:00"
        ))

    # 1,500 students, 3 section enrollments each
    for i in range(1500):

        student_id = f"STU{i + 1:04d}"

        for offset in range(3):

            section_number = ((i * 3 + offset * 40) % 120) + 1

            section_id = f"SEC{section_number:03d}"

            cur.execute("""
                INSERT INTO enrollments
                VALUES (?, ?)
            """, (student_id, section_id))

    con.commit()
    con.close()


def get_counts():

    con = connect()
    cur = con.cursor()

    tables = [
        "students",
        "faculty",
        "courses",
        "rooms",
        "sections",
        "enrollments"
    ]

    counts = {}

    for table in tables:

        cur.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cur.fetchone()[0]

    con.close()

    return counts


if __name__ == "__main__":

    load_demo_data()

    print("Competition-scale test data created!")
    print(get_counts())
