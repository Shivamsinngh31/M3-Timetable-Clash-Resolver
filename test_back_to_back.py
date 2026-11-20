
import sqlite3
from datetime import datetime

con = sqlite3.connect("timetable.db")
cur = con.cursor()

cur.execute("""
    SELECT
        e.student_id,
        s.day,
        s.start_time,
        s.end_time,
        s.section_id
    FROM enrollments e
    JOIN sections s
        ON e.section_id = s.section_id
    ORDER BY e.student_id, s.day, s.start_time
""")

records = cur.fetchall()
con.close()

print("\nBACK-TO-BACK LECTURE TEST")
print("-------------------------")

student_classes = {}

for student, day, start, end, section in records:
    key = (student, day)
    student_classes.setdefault(key, []).append(
        (start, end, section)
    )

violations = []

for (student, day), classes in student_classes.items():
    consecutive = 1

    for i in range(1, len(classes)):
        previous_end = datetime.strptime(
            classes[i - 1][1], "%H:%M"
        )
        current_start = datetime.strptime(
            classes[i][0], "%H:%M"
        )

        if previous_end == current_start:
            consecutive += 1
        else:
            consecutive = 1

        if consecutive > 3:
            violations.append((student, day, classes[i][2]))

if violations:
    print("FAIL: More than 3 consecutive lectures found.")

    for violation in violations:
        print(violation)
else:
    print("PASS: No student has more than 3 consecutive lectures.")
