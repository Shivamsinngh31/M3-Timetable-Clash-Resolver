
import sqlite3
import shutil
import tempfile
import os

import scheduler

original_db = "timetable.db"
test_db = None

try:
    # Create a temporary copy of the database
    temp_file = tempfile.NamedTemporaryFile(
        suffix=".db", delete=False
    )
    test_db = temp_file.name
    temp_file.close()

    shutil.copy2(original_db, test_db)

    # Make the scheduler use the temporary database
    scheduler.DB_NAME = test_db

    con = sqlite3.connect(test_db)
    cur = con.cursor()

    # Get two sections
    cur.execute("""
        SELECT section_id, faculty_id, room_id,
               day, start_time, end_time
        FROM sections
        ORDER BY section_id
        LIMIT 2
    """)

    sections = cur.fetchall()

    if len(sections) < 2:
        print("Not enough sections to test.")
    else:
        first = sections[0]
        second = sections[1]

        # Get one student from the first section
        cur.execute("""
            SELECT student_id
            FROM enrollments
            WHERE section_id = ?
            LIMIT 1
        """, (first[0],))

        student = cur.fetchone()

        # Force the second section to conflict
        cur.execute("""
            UPDATE sections
            SET faculty_id = ?,
                room_id = ?,
                day = ?,
                start_time = ?,
                end_time = ?
            WHERE section_id = ?
        """, (
            first[1],
            first[2],
            first[3],
            first[4],
            first[5],
            second[0]
        ))

        if student:
            cur.execute("""
                INSERT OR IGNORE INTO enrollments
                VALUES (?, ?)
            """, (student[0], second[0]))

        con.commit()
        con.close()

        # Run the actual clash checker
        results = scheduler.check_clashes()

        print("\nCLASH DETECTION TEST RESULTS")
        print("----------------------------")

        for result in results:
            print(result)

        student_found = any(
            x.startswith("Student clash:")
            for x in results
        )

        faculty_found = any(
            x.startswith("Faculty clash:")
            for x in results
        )

        room_found = any(
            x.startswith("Classroom clash:")
            for x in results
        )

        print("\nFINAL TEST STATUS")
        print("-----------------")
        print("Student detection:", student_found)
        print("Faculty detection:", faculty_found)
        print("Classroom detection:", room_found)

finally:
    # Restore the normal database setting
    scheduler.DB_NAME = original_db

    # Delete the temporary test database
    if test_db and os.path.exists(test_db):
        os.remove(test_db)
