""" Domain-Objects (SQL-Alchemy database model) for students' database """

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

from sqlalchemy_utils.functions import create_database
from sqlalchemy_utils.functions import database_exists
from sqlalchemy_utils.functions import drop_database

Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relationship("Group", back_populates="students")
    grades = relationship("Grade", back_populates="student")


class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    students = relationship("Student", back_populates="group")
    def size(self):
        return len(self.students)
    def __str__(self):
        return f"group(\"{self.name}\" of {self.size()} students)"

class Teacher(Base):
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    subjects = relationship("Subject", back_populates="teacher")
    def __str__(self):
        return f"teacher'{self.name}')"


class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
    teacher = relationship("Teacher", back_populates="subjects")
    grades = relationship("Grade", back_populates="subject")
    def __str__(self):
        return f"subject<{self.name} by {self.teacher}>"


class Grade(Base):
    __tablename__ = 'grades'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    grade = Column(Integer)
    date = Column(DateTime)
    student = relationship("Student", back_populates="grades")
    subject = relationship("Subject", back_populates="grades")
    def __str__(self):
        return f"grade[{self.grade} at {self.date}]"

# TODO: think about moving the database connection string to a dedicated config
DATABASE_URL = "sqlite:///school.db"

def recreate_database():
    if database_exists(DATABASE_URL):
        # TODO: thinks about just executing << Base.metadata.drop_all(engine) >>
        print(f"database '{DATABASE_URL}' exists - going to drop it")
        drop_database(DATABASE_URL)
    print(f"going to create the database '{DATABASE_URL}'")
    create_database(DATABASE_URL)
    print(f"database '{DATABASE_URL}' was created")

    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    recreate_database()