# SASTRA Timetable Generation

## 🚀 Features

- **Automated Timetable Generation:** Dynamically generates schedules without time or venue clashes.
- **Conflict Resolution:** Ensures no overlap of classes for faculty or students.
- **Flexible Design:** Supports elective courses, multiple sections, and variable room capacities.
- **User-Friendly Interface:** Built with a responsive front end for easy interaction.
- **Real-Time Updates:** Updates schedules instantly upon data changes.

## 🛠️ Tools & Technologies Used

- **Backend:** [Flask](https://flask.palletsprojects.com/en/stable/) (Python)
- **Frontend:** [HTML](https://html.com/), [CSS](https://css3.com/), [JavaScript](https://www.javascript.com/)
- **Database:** [MySQL](https://www.mysql.com/)
- **Visualization:** [Mermaid.js](https://mermaid-js.github.io/) for ER diagrams

## 🎯 Project Mission

At SASTRA, the pursuit of academic excellence has always been supported by innovation. This project aligns with that legacy by removing the burden of manual timetable calculation. 

The goal is simple: **Let people focus on teaching and learning — not on figuring out class schedules.**

Through precise rule enforcement, the system prevents common scheduling issues, like:

- Double-booked rooms or faculties
- Elective clashes across sections
- Invalid class-to-stream/course mappings


## 🏗️ Database & Schema Design

The database is meticulously designed with normalized tables, optimized queries, and robust constraints. Key components include:

- **Campus, Schools, Departments** for organizing physical locations
- **Sections, Streams, Programmes, Courses** for curriculum management
- **Faculty, Students, Classes** for mapping human and infrastructure resources

Triggers, stored procedures, and functions enforce data integrity, while the system architecture supports easy scalability.
