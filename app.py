
import streamlit as st
import pandas as pd
import sqlite3
import time

from database import load_demo_data, get_counts
from scheduler import generate_timetable, check_clashes

st.set_page_config(
    page_title="M3 Timetable Clash Resolver",
    page_icon="📅",
    layout="wide"
)

st.title("📅 M3 Timetable Clash Resolver")
st.write("Automatic timetable generation and clash detection system.")

st.sidebar.title("Navigation")

menu = st.sidebar.selectbox(
    "Select Option",
    [
        "Dashboard",
        "Generate Timetable",
        "View Timetable",
        "Check Clashes"
    ]
)

if "data_loaded" not in st.session_state:
    load_demo_data()
    st.session_state.data_loaded = True

counts = get_counts()


def get_data(query):

    con = sqlite3.connect("timetable.db")
    df = pd.read_sql_query(query, con)
    con.close()

    return df


# DASHBOARD
if menu == "Dashboard":

    st.header("Project Dashboard")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Students", counts["students"])
    col2.metric("Total Faculty", counts["faculty"])
    col3.metric("Total Sections", counts["sections"])

    col4, col5, col6 = st.columns(3)

    col4.metric("Total Courses", counts["courses"])
    col5.metric("Total Classrooms", counts["rooms"])
    col6.metric("Total Enrollments", counts["enrollments"])

    st.info("Use the sidebar to manage and generate your timetable.")

    st.subheader("Student Details")

    students = get_data("""
        SELECT student_id, name, semester
        FROM students
        ORDER BY student_id
    """)

    st.dataframe(students, use_container_width=True)

    st.subheader("Faculty Details")

    faculty = get_data("""
        SELECT faculty_id, name
        FROM faculty
        ORDER BY faculty_id
    """)

    st.dataframe(faculty, use_container_width=True)

    st.subheader("Course Details")

    courses = get_data("""
        SELECT course_id, course_name
        FROM courses
        ORDER BY course_id
    """)

    st.dataframe(courses, use_container_width=True)

    st.subheader("Classroom Details")

    rooms = get_data("""
        SELECT room_id, room_name, capacity
        FROM rooms
        ORDER BY room_id
    """)

    st.dataframe(rooms, use_container_width=True)


# GENERATE TIMETABLE
elif menu == "Generate Timetable":

    st.header("Generate Timetable")

    st.write(
        "Generate a timetable while respecting "
        "student, faculty and classroom constraints."
    )

    if st.button("Generate Timetable", type="primary"):

        with st.spinner("Generating timetable..."):

            start_time = time.perf_counter()

            success, message, timetable = generate_timetable()

            end_time = time.perf_counter()

            generation_time = end_time - start_time

        if success:

            st.success(message)

            st.metric(
                "Timetable Generation Time",
                f"{generation_time:.2f} seconds"
            )

            st.session_state.timetable_generated = True

            st.subheader("Generated Timetable")

            df = pd.DataFrame(timetable)

            st.dataframe(df, use_container_width=True)

            if generation_time <= 60:
                st.success("Generation completed within the 60-second target.")
            else:
                st.warning("Generation exceeded the 60-second target.")

        else:

            st.error(message)

            st.metric(
                "Timetable Generation Time",
                f"{generation_time:.2f} seconds"
            )


# VIEW TIMETABLE
elif menu == "View Timetable":

    st.header("Generated Timetable")

    df = get_data("""
        SELECT
            sections.section_id,
            courses.course_name,
            faculty.name AS faculty_name,
            rooms.room_name,
            sections.day,
            sections.start_time,
            sections.end_time
        FROM sections
        JOIN courses
            ON sections.course_id = courses.course_id
        JOIN faculty
            ON sections.faculty_id = faculty.faculty_id
        JOIN rooms
            ON sections.room_id = rooms.room_id
        ORDER BY
            CASE sections.day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
            END,
            sections.start_time
    """)

    if st.session_state.get("timetable_generated", False):

        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Timetable CSV",
            data=csv,
            file_name="generated_timetable.csv",
            mime="text/csv"
        )

    else:

        st.warning("Please generate the timetable first.")


# CHECK CLASHES
elif menu == "Check Clashes":

    st.header("Timetable Clash Checker")

    st.write(
        "Check student, faculty, classroom, capacity "
        "and back-to-back lecture constraints."
    )

    if st.button("Check Clashes", type="primary"):

        clashes = check_clashes()

        student_clashes = [
            x for x in clashes if x.startswith("Student clash:")
        ]

        faculty_clashes = [
            x for x in clashes if x.startswith("Faculty clash:")
        ]

        room_clashes = [
            x for x in clashes if x.startswith("Classroom clash:")
        ]

        consecutive_clashes = [
            x for x in clashes
            if x.startswith("Back-to-back violation:")
        ]

        capacity_clashes = get_data("""
            SELECT
                sections.section_id,
                rooms.room_name,
                rooms.capacity,
                COUNT(enrollments.student_id) AS enrolled_students
            FROM sections
            JOIN rooms
                ON sections.room_id = rooms.room_id
            LEFT JOIN enrollments
                ON sections.section_id = enrollments.section_id
            GROUP BY
                sections.section_id,
                rooms.room_name,
                rooms.capacity
            HAVING COUNT(enrollments.student_id) > rooms.capacity
        """)

        st.subheader("Validation Results")

        col1, col2, col3 = st.columns(3)

        col1.metric("Student Clashes", len(student_clashes))
        col2.metric("Faculty Clashes", len(faculty_clashes))
        col3.metric("Classroom Clashes", len(room_clashes))

        col4, col5 = st.columns(2)

        col4.metric("Capacity Violations", len(capacity_clashes))
        col5.metric(
            "Back-to-back Violations",
            len(consecutive_clashes)
        )

        if clashes or not capacity_clashes.empty:

            st.error("Some timetable violations were found.")

            for clash in student_clashes:
                st.write("❌", clash)

            for clash in faculty_clashes:
                st.write("❌", clash)

            for clash in room_clashes:
                st.write("❌", clash)

            for clash in consecutive_clashes:
                st.write("❌", clash)

            if not capacity_clashes.empty:

                st.subheader("Room Capacity Violations")

                st.dataframe(
                    capacity_clashes,
                    use_container_width=True
                )

        else:

            st.success(
                "All five validation checks passed. "
                "No violations found."
            )
