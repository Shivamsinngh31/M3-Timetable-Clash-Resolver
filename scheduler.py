
import sqlite3
from collections import defaultdict

DB_NAME = "timetable.db"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

TIME_SLOTS = [
    ("09:00", "10:00"),
    ("10:00", "11:00"),
    ("11:00", "12:00"),
    ("12:00", "13:00"),
    ("14:00", "15:00"),
    ("15:00", "16:00"),
    ("16:00", "17:00")
]


def connect():
    return sqlite3.connect(DB_NAME)


def generate_timetable():
    con = connect()

    try:
        cur = con.cursor()

        cur.execute("""
            SELECT section_id, course_id, faculty_id
            FROM sections
        """)
        sections = cur.fetchall()

        cur.execute("SELECT room_id, capacity FROM rooms")
        rooms = cur.fetchall()

        cur.execute("SELECT student_id, section_id FROM enrollments")
        enrollments = cur.fetchall()

        if not sections:
            return False, "No sections found.", []

        if not rooms:
            return False, "No classrooms found.", []

        section_students = defaultdict(set)

        for student_id, section_id in enrollments:
            section_students[section_id].add(student_id)

        for section_id, _, _ in sections:
            required = len(section_students[section_id])

            if not any(capacity >= required for _, capacity in rooms):
                return False, f"No suitable room for {section_id}.", []

        # Schedule larger sections first.
        ordered_sections = sorted(
            sections,
            key=lambda item: len(section_students[item[0]]),
            reverse=True
        )

        # Try several different scheduling orders.
        for attempt in range(15):

            faculty_used = set()
            room_used = set()
            student_used = defaultdict(set)
            student_days = defaultdict(lambda: defaultdict(set))
            timetable = []

            # Change section order slightly between attempts.
            if attempt:
                ordered = sorted(
                    sections,
                    key=lambda item: (
                        -len(section_students[item[0]]),
                        (hash(str(item[0])) + attempt * 17) % 97
                    )
                )
            else:
                ordered = ordered_sections

            success = True

            for section_id, course_id, faculty_id in ordered:

                students = section_students[section_id]
                required = len(students)

                suitable_rooms = sorted(
                    [r for r in rooms if r[1] >= required],
                    key=lambda r: r[1]
                )

                placed = False

                for day_index, day in enumerate(DAYS):
                    for slot_index, (start, end) in enumerate(TIME_SLOTS):

                        # Faculty availability.
                        if (faculty_id, day_index, slot_index) in faculty_used:
                            continue

                        # Student availability and consecutive lecture check.
                        valid = True

                        for student_id in students:

                            if (day_index, slot_index) in student_used[student_id]:
                                valid = False
                                break

                            occupied = student_days[student_id][day_index]

                            before = slot_index - 1
                            after = slot_index + 1
                            count = 1

                            while (
                                before >= 0
                                and TIME_SLOTS[before][1] == TIME_SLOTS[before + 1][0]
                                and before in occupied
                            ):
                                count += 1
                                before -= 1

                            while (
                                after < len(TIME_SLOTS)
                                and TIME_SLOTS[after - 1][1] == TIME_SLOTS[after][0]
                                and after in occupied
                            ):
                                count += 1
                                after += 1

                            if count > 3:
                                valid = False
                                break

                        if not valid:
                            continue

                        # Find an available suitable classroom.
                        room_id = None

                        for candidate_room, capacity in suitable_rooms:
                            if (candidate_room, day_index, slot_index) not in room_used:
                                room_id = candidate_room
                                break

                        if room_id is None:
                            continue

                        # Save this section's assignment.
                        faculty_used.add((faculty_id, day_index, slot_index))
                        room_used.add((room_id, day_index, slot_index))

                        for student_id in students:
                            student_used[student_id].add((day_index, slot_index))
                            student_days[student_id][day_index].add(slot_index)

                        timetable.append({
                            "section_id": section_id,
                            "room_id": room_id,
                            "day": day,
                            "start_time": start,
                            "end_time": end
                        })

                        placed = True
                        break

                    if placed:
                        break

                if not placed:
                    success = False
                    break

            if success:
                for item in timetable:
                    cur.execute("""
                        UPDATE sections
                        SET room_id = ?,
                            day = ?,
                            start_time = ?,
                            end_time = ?
                        WHERE section_id = ?
                    """, (
                        item["room_id"],
                        item["day"],
                        item["start_time"],
                        item["end_time"],
                        item["section_id"]
                    ))

                con.commit()
                return True, "Timetable generated successfully!", timetable

        return (
            False,
            "Could not find a valid timetable. Please try again.",
            []
        )

    except Exception as e:
        con.rollback()
        return False, f"Timetable generation error: {str(e)}", []

    finally:
        con.close()


def check_clashes():
    con = connect()

    try:
        cur = con.cursor()

        cur.execute("""
            SELECT section_id, faculty_id, room_id,
                   day, start_time, end_time
            FROM sections
        """)
        sections = cur.fetchall()

        cur.execute("""
            SELECT student_id, section_id
            FROM enrollments
        """)
        enrollments = cur.fetchall()

    finally:
        con.close()

    clashes = []

    def overlaps(a_start, a_end, b_start, b_end):
        return a_start < b_end and b_start < a_end

    section_students = defaultdict(set)

    for student_id, section_id in enrollments:
        section_students[section_id].add(student_id)

    for section in sections:
        section_id, faculty, room, day, start, end = section

        if start and end and start < "14:00" and end > "13:00":
            clashes.append(f"Lunch break violation: {section_id} on {day}")

    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):

            a = sections[i]
            b = sections[j]

            if not a[3] or a[3] != b[3]:
                continue

            if not a[4] or not a[5] or not b[4] or not b[5]:
                continue

            if not overlaps(a[4], a[5], b[4], b[5]):
                continue

            if a[1] == b[1]:
                clashes.append(f"Faculty clash: {a[1]} between {a[0]} and {b[0]}")

            if a[2] == b[2]:
                clashes.append(f"Classroom clash: {a[2]} between {a[0]} and {b[0]}")

            common = section_students[a[0]] & section_students[b[0]]

            for student_id in common:
                clashes.append(f"Student clash: {student_id} between {a[0]} and {b[0]}")

    student_lectures = defaultdict(list)

    for section in sections:
        section_id, _, _, day, start, end = section

        if not day or not start or not end:
            continue

        for student_id in section_students[section_id]:
            student_lectures[student_id].append((day, start, end, section_id))

    for student_id, lectures in student_lectures.items():
        lectures.sort(key=lambda item: (item[0], item[1]))
        consecutive = 1

        for i in range(1, len(lectures)):
            previous = lectures[i - 1]
            current = lectures[i]

            if previous[0] == current[0] and previous[2] == current[1]:
                consecutive += 1

                if consecutive > 3:
                    clashes.append(
                        f"Back-to-back violation: {student_id} "
                        f"has more than 3 consecutive lectures on {current[0]}"
                    )
            else:
                consecutive = 1

    return list(set(clashes))
