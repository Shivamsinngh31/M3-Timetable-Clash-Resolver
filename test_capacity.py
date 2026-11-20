
import sqlite3

con = sqlite3.connect("timetable.db")
cur = con.cursor()

cur.execute("""
    SELECT
        sections.section_id,
        rooms.room_name,
        rooms.capacity,
        COUNT(enrollments.student_id) AS total_students
    FROM sections
    JOIN rooms
        ON sections.room_id = rooms.room_id
    LEFT JOIN enrollments
        ON sections.section_id = enrollments.section_id
    GROUP BY sections.section_id
""")

results = cur.fetchall()

print("\nCLASSROOM CAPACITY TEST")
print("-----------------------")

violations = 0

for section, room, capacity, students in results:
    if students > capacity:
        violations += 1
        print(
            f"FAIL: {section} has {students} students, "
            f"but {room} capacity is {capacity}."
        )

if violations == 0:
    print("PASS: All classrooms have sufficient capacity.")
else:
    print("Total capacity violations:", violations)

con.close()
