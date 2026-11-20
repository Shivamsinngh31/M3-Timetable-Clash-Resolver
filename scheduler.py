
import sqlite3
from collections import defaultdict
from ortools.sat.python import cp_model

DB_NAME = "timetable.db"

DAYS = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday"
]

# Lunch break: 1 PM to 2 PM
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


# GENERATE TIMETABLE
def generate_timetable():

    con = connect()
    cur = con.cursor()

    try:
        cur.execute("""
            SELECT section_id, course_id, faculty_id
            FROM sections
        """)
        sections = cur.fetchall()

        cur.execute("""
            SELECT room_id, capacity
            FROM rooms
        """)
        rooms = cur.fetchall()

        cur.execute("""
            SELECT student_id, section_id
            FROM enrollments
        """)
        enrollments = cur.fetchall()

        if not sections:
            return False, "No sections found.", []

        if not rooms:
            return False, "No classrooms found.", []

        # Store students section-wise
        section_students = defaultdict(list)

        for student_id, section_id in enrollments:
            section_students[section_id].append(student_id)

        # Check classroom capacity
        for section_id, course_id, faculty_id in sections:

            required_seats = len(section_students[section_id])

            if not any(
                capacity >= required_seats
                for room_id, capacity in rooms
            ):
                return (
                    False,
                    f"Room capacity conflict for {section_id}. "
                    f"Required seats: {required_seats}",
                    []
                )

        # Create constraint model
        model = cp_model.CpModel()

        x = {}

        section_options = defaultdict(list)
        faculty_options = defaultdict(list)
        room_options = defaultdict(list)

        # Stores room alternatives for each section and time slot
        section_slot_options = defaultdict(list)

        # Create scheduling variables
        for section_id, course_id, faculty_id in sections:

            required_seats = len(section_students[section_id])

            for day_index, day in enumerate(DAYS):

                for slot_index, (start, end) in enumerate(TIME_SLOTS):

                    for room_id, capacity in rooms:

                        if capacity < required_seats:
                            continue

                        key = (
                            section_id,
                            day_index,
                            slot_index,
                            room_id
                        )

                        variable = model.NewBoolVar(
                            f"{section_id}_{day_index}_{slot_index}_{room_id}"
                        )

                        x[key] = variable

                        section_options[section_id].append(variable)

                        faculty_options[
                            (faculty_id, day_index, slot_index)
                        ].append(variable)

                        room_options[
                            (room_id, day_index, slot_index)
                        ].append(variable)

                        section_slot_options[
                            (section_id, day_index, slot_index)
                        ].append(variable)

        # Every section must be scheduled exactly once
        for section_id, course_id, faculty_id in sections:

            model.Add(
                sum(section_options[section_id]) == 1
            )

        # Faculty cannot teach two sections at the same time
        for variables in faculty_options.values():
            model.Add(sum(variables) <= 1)

        # Room cannot host two sections at the same time
        for variables in room_options.values():
            model.Add(sum(variables) <= 1)

        # Create one expression per section and time slot.
        # This avoids repeating every classroom variable for every student.
        section_slot_presence = {}

        for key, variables in section_slot_options.items():

            section_slot_presence[key] = sum(variables)

        # Student scheduling options
        student_options = defaultdict(list)

        for section_id, students in section_students.items():

            for day_index in range(len(DAYS)):

                for slot_index in range(len(TIME_SLOTS)):

                    presence = section_slot_presence.get(
                        (section_id, day_index, slot_index)
                    )

                    if presence is not None:

                        for student_id in students:

                            student_options[
                                (student_id, day_index, slot_index)
                            ].append(presence)

        # Student cannot attend two sections at the same time
        for variables in student_options.values():
            model.Add(sum(variables) <= 1)

        # Maximum three consecutive lectures per student
        for student_id in section_students:

            for day_index in range(len(DAYS)):

                for start_index in range(len(TIME_SLOTS) - 3):

                    window = TIME_SLOTS[
                        start_index:start_index + 4
                    ]

                    # Do not count across the lunch break
                    continuous = all(
                        window[i][1] == window[i + 1][0]
                        for i in range(3)
                    )

                    if not continuous:
                        continue

                    variables = []

                    for slot_index in range(
                        start_index,
                        start_index + 4
                    ):

                        variables.extend(
                            student_options.get(
                                (student_id, day_index, slot_index),
                                []
                            )
                        )

                    model.Add(sum(variables) <= 3)

        # Prefer earlier days and time slots
        objective_terms = []

        for key, variable in x.items():

            section_id, day_index, slot_index, room_id = key

            cost = day_index * 7 + slot_index

            objective_terms.append(cost * variable)

        model.Minimize(sum(objective_terms))

        # Solve model
        solver = cp_model.CpSolver()

        solver.parameters.max_time_in_seconds = 25
        solver.parameters.num_search_workers = 1

        status = solver.Solve(model)

        if status not in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE
        ):

            if status == cp_model.INFEASIBLE:
                return (
                    False,
                    "No feasible timetable exists for the current constraints.",
                    []
                )

            if status == cp_model.UNKNOWN:
                return (
                    False,
                    "Time limit reached. No solution was found.",
                    []
                )

            return False, "Unable to generate timetable.", []

        # Collect scheduled sections
        timetable = []

        for key, variable in x.items():

            if solver.Value(variable) == 1:

                section_id, day_index, slot_index, room_id = key

                start, end = TIME_SLOTS[slot_index]

                timetable.append({
                    "section_id": section_id,
                    "room_id": room_id,
                    "day": DAYS[day_index],
                    "start_time": start,
                    "end_time": end
                })

        # Save timetable
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

    except Exception as e:

        con.rollback()

        return False, f"Timetable generation error: {str(e)}", []

    finally:
        con.close()


# CHECK ALL TIMETABLE CLASHES
def check_clashes():

    con = connect()
    cur = con.cursor()

    try:
        cur.execute("""
            SELECT
                section_id,
                faculty_id,
                room_id,
                day,
                start_time,
                end_time
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

        return (
            a_start < b_end
            and b_start < a_end
        )

    # Check lunch break violations
    for section in sections:

        section_id = section[0]
        day = section[3]
        start = section[4]
        end = section[5]

        if start and end and start < "14:00" and end > "13:00":

            clashes.append(
                f"Lunch break violation: {section_id} on {day}"
            )

    # Student enrollments
    section_students = defaultdict(list)

    for student_id, section_id in enrollments:
        section_students[section_id].append(student_id)

    # Check faculty, classroom and student clashes
    for i in range(len(sections)):

        for j in range(i + 1, len(sections)):

            a = sections[i]
            b = sections[j]

            if not a[3] or not b[3]:
                continue

            if a[3] != b[3]:
                continue

            if not a[4] or not a[5] or not b[4] or not b[5]:
                continue

            if not overlaps(a[4], a[5], b[4], b[5]):
                continue

            if a[1] == b[1]:

                clashes.append(
                    f"Faculty clash: {a[1]} "
                    f"between {a[0]} and {b[0]}"
                )

            if a[2] == b[2]:

                clashes.append(
                    f"Classroom clash: {a[2]} "
                    f"between {a[0]} and {b[0]}"
                )

            common_students = (
                set(section_students[a[0]])
                & set(section_students[b[0]])
            )

            for student_id in common_students:

                clashes.append(
                    f"Student clash: {student_id} "
                    f"between {a[0]} and {b[0]}"
                )

    # Check maximum three consecutive lectures
    student_lectures = defaultdict(list)

    for section in sections:

        section_id = section[0]
        day = section[3]
        start = section[4]
        end = section[5]

        if not day or not start or not end:
            continue

        for student_id in section_students[section_id]:

            student_lectures[student_id].append(
                (day, start, end, section_id)
            )

    for student_id, lectures in student_lectures.items():

        lectures.sort(key=lambda item: (item[0], item[1]))

        consecutive_count = 1

        for i in range(1, len(lectures)):

            previous = lectures[i - 1]
            current = lectures[i]

            if (
                previous[0] == current[0]
                and previous[2] == current[1]
            ):

                consecutive_count += 1

                if consecutive_count > 3:

                    clashes.append(
                        f"Back-to-back violation: {student_id} "
                        f"has more than 3 consecutive lectures "
                        f"on {current[0]}"
                    )

            else:

                consecutive_count = 1

    return list(set(clashes))
