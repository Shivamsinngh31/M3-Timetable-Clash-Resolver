
import sqlite3

con = sqlite3.connect("timetable.db")
cur = con.cursor()

cur.execute("""
    SELECT section_id, day, start_time, end_time
    FROM sections
    WHERE start_time < '14:00'
      AND end_time > '13:00'
""")

violations = cur.fetchall()

print("\nLUNCH BREAK TEST")
print("----------------")

if violations:
    print("FAIL: Lectures found during lunch break.")

    for item in violations:
        print(item)
else:
    print("PASS: No lectures scheduled during 1 PM to 2 PM.")

con.close()
