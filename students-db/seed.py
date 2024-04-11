""" Loading the data (using 'faker' and 'random') into students' database (SQLite and SQL-Alchemy) """

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Student, Group, Teacher, Subject, Grade, DATABASE_URL

import faker

GROUPS_COUNT = 3
TEACHERS_COUNT = 7
STUDENTS_COUNT = 30
RANDOM_SEED = 123

SUBJECTS = ["Mathematics", "Literature", "Physics", "Chemistry", "English",
            "Biology", "Geography", "History"]

fake = faker.Faker()
fake.seed_instance(RANDOM_SEED)
rnd = fake.random
rnd.seed(RANDOM_SEED)

print(f"Going to seed the database '{DATABASE_URL}' with following parameters:")
print(f"- {GROUPS_COUNT = }")
print(f"- {TEACHERS_COUNT = }")
print(f"- {STUDENTS_COUNT = }")
print(f"- {len(SUBJECTS) = }")
print(f"- {RANDOM_SEED = }")

# Підключення до бази даних
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

# Створення груп
fn_group_name = lambda group_number: f'Group #{group_number}'
groups = [Group(name=fn_group_name(i+1)) for i in range(GROUPS_COUNT)]
session.add_all(groups)
session.commit()

# Створення викладачів
teachers = [Teacher(name=fake.name()) for _ in range(TEACHERS_COUNT)]
session.add_all(teachers)
session.commit()

# Створення предметів
subjects = [Subject(name=s, teacher=rnd.choice(teachers)) for s in SUBJECTS]
session.add_all(subjects)
session.commit()

# Створення студентів та їх оцінок
for _ in range(STUDENTS_COUNT):
    student = Student(name=fake.name(), group=rnd.choice(groups))
    session.add(student)
    for subject in subjects:
        for _ in range(rnd.randint(3, 5)):
            grade_date = fake.date_time_between(start_date='-1y', end_date='now')
            grade_value = rnd.randint(20, 100)
            grade = Grade(student=student, subject=subject, grade=grade_value, date=grade_date)
            session.add(grade)

session.commit()
print("Database seeding is completed!")
print("===========================")
print()

