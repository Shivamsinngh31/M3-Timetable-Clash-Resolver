
import sqlite3
from collections import defaultdict
from ortools.sat.python import cp_model

DB_NAME = "timetable.db"

DAYS = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday"
]

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

        section_students = defaultdict(set)
        student_sections = defaultdict(set)

        for student_id, section_id in enrollments:
            section_students[section_id].add(student_id)
            student_sections[student_id].add(section_id)

        section_info = {}

        for section_id, course_id, faculty_id in sections:
            required = len(section_students[section_id])

            if not any(capacity >= required for _, capacity in rooms):
                return (
                    False,
                    f"Room capacity conflict for {section_id}. "
                    f"Required seats: {required}",
                    []
                )

            section_info[section_id] = {
                "faculty": faculty_id,
                "students": required
            }

        model = cp_model.CpModel()

        x = {}
        section_options = defaultdict(list)
        faculty_options = defaultdict(list)
        slot_options = defaultdict(list)

        # Create one variable per section, day and time.
        for section_id, course_id, faculty_id in sections:
            for day_index in range(len(DAYS)):
                for slot_index in range(len(TIME_SLOTS)):

                    variable = model.NewBoolVar(
                        f"{section_id}_{day_index}_{slot_index}"
                    )

                    key = (section_id, day_index, slot_index)
                    x[key] = variable

                    section_options[section_id].append(variable)

                    faculty_options[
                        (faculty_id, day_index, slot_index)
                    ].append(variable)

                    slot_options[
                        (day_index, slot_index)
                    ].append(variable)

        # Every section must be scheduled exactly once.
        for section_id, _, _ in sections:
            model.Add(sum(section_options[section_id]) == 1)

        # Faculty cannot teach two sections at the same time.
        for variables in faculty_options.values():
            model.Add(sum(variables) <= 1)

        # Check classroom availability and capacity.
        # Larger sections must have access to sufficiently large rooms.
        unique_demands = sorted({
            info["students"] for info in section_info.values()
        })

        for day_index in range(len(DAYS)):
            for slot_index in range(len(TIME_SLOTS)):

                variables = slot_options[(day_index, slot_index)]

                model.Add(sum(variables) <= len(rooms))

                for demand in unique_demands:
                    eligible_rooms = sum(
                        1 for _, capacity in rooms
                        if capacity >= demand
                    )

                    large_sections = [
                        x[(section_id, day_index, slot_index)]
                        for section_id in section_info
                        if section_info[section_id]["students"] >= demand
                    ]

                    if large_sections:
                        model.Add(
                            sum(large_sections) <= eligible_rooms
                        )

        # Student cannot attend two sections at the same time.
        for student_id, enrolled_sections in student_sections.items():

            for day_index in range(len(DAYS)):
                for slot_index in range(len(TIME_SLOTS)):

                    variables = [
                        x[(section_id, day_index, slot_index)]
                        for section_id in enrolled_sections
                    ]

                    if variables:
                        model.Add(sum(variables) <= 1)

        # Maximum three consecutive lectures per student.
        for student_id, enrolled_sections in student_sections.items():

            for day_index in range(len(DAYS)):

                for start_index in range(len(TIME_SLOTS) - 3):

                    window = TIME_SLOTS[
                        start_index:start_index + 4
                    ]

                    continuous = all(
                        window[i][1] == window[i + 1][0]
                        for i in range(3)
                    )

                    if not continuous:
                        continue

                    variables = []

                    for slot_index in range(
                        start_index, start_index + 4
                    ):
                        for section_id in enrolled_sections:
                            variables.append(
                                x[(section_id, day_index, slot_index)]
                            )

                    model.Add(sum(variables) <= 3)

        # Prefer earlier days and time slots.
        objective_terms = []

        for (section_id, day_index, slot_index), variable in x.items():
            cost = day_index * 7 + slot_index
            objective_terms.append(cost * variable)

        model.Minimize(sum(objective_terms))

        # Solve model.
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 25
        solver.parameters.num_search_workers = 1

        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if status == cp_model.INFEASIBLE:
                return (
                    False,
                    "No feasible timetable exists for the current constraints.",
                    []
                )

            return (
                False,
                "Time limit reached or no solution was found.",
                []
            )

        # Collect scheduled sections by day and time.
        scheduled_slots = defaultdict(list)

        for (section_id, day_index, slot_index), variable in x.items():

            if solver.Value(variable) == 1:
                scheduled_slots[
                    (day_index, slot_index)
                ].append(section_id)

        # Assign classrooms after solving.
        timetable = []

        sorted_rooms = sorted(rooms, key=lambda item: item[1])

        for (day_index, slot_index), section_ids in scheduled_slots.items():

            section_ids.sort(
                key=lambda section_id: section_info[section_id]["students"],
                reverse=True
            )

            available_rooms = sorted_rooms.copy()

            for section_id in section_ids:

                required = section_info[section_id]["students"]

                suitable_rooms = [
                    room for room in available_rooms
                    if room[1] >= required
                ]

                if not suitable_rooms:
                    return (
                        False,
                        "Unable to assign suitable classrooms. "
                        "Please check room capacities.",
                        []
                    )

                room_id, capacity = suitable_rooms[0]
                available_rooms.remove((room_id, capacity))

                start, end = TIME_SLOTS[slot_index]

                timetable.append({
                    "section_id": section_id,
                    "room_id": room_id,
                    "day": DAYS[day_index],
                    "start_time": start,
                    "end_time": end
                })

        # Save timetable.
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

    # Check lunch break violations.
    for section in sections:
        section_id = section[0]
        day = section[3]
        start = section[4]
        end = section[5]

        if start and end and start < "14:00" and end > "13:00":
            clashes.append(
                f"Lunch break violation: {section_id} on {day}"
            )

    section_students = defaultdict(set)

    for student_id, section_id in enrollments:
        section_students[section_id].add(student_id)

    # Check faculty, classroom and student clashes.
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):

            a = sections[i]
            b = sections[j]

            if not a[3] or not b[3] or a[3] != b[3]:
                continue

            if not a[4] or not a[5] or not b[4] or not b[5]:
                continue

            if not overlaps(a[4], a[5], b[4], b[5]):
                continue

            if a[1] == b[1]:
                clashes.append(
                    f"Faculty clash: {a[1]} between {a[0]} and {b[0]}"
                )

            if a[2] == b[2]:
                clashes.append(
                    f"Classroom clash: {a[2]} between {a[0]} and {b[0]}"
                )

            common_students = (
                section_students[a[0]] & section_students[b[0]]
            )

            for student_id in common_students:
                clashes.append(
                    f"Student clash: {student_id} between {a[0]} and {b[0]}"
                )

    # Check maximum three consecutive lectures.
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
