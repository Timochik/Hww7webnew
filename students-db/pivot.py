""" Calculating Pivot-Data in students' database (powered by SQL-Alchemy) """

import sys
from collections import namedtuple

from rich.console import Console
from sqlalchemy import text, select, func

from models import Student, Grade

def to_dict(ntpl):
    return {name: value for (name, value) in ntpl._asdict().items()
            if value is not None and value != 0}
def key_of_value(ntpl) -> str:
    items = to_dict(ntpl).items()
    return "TOTAL" if len(items) == 0 else ", ".join([f"{name}({value})" for (name, value) in items])
def key_is_value(ntpl) -> str:
    items = to_dict(ntpl).items()
    return "TOTAL" if len(items) == 0 else ", ".join([f"{name}:{value}" for (name, value) in items])


# namedtuple of optional student_id, group_id and subject_id
PivotKeyIDs = namedtuple('PivotKeyIDs', 'subject_id group_id student_id')
PivotKeyIDs.__new__.__defaults__ = (None, None, None)
PivotKeyIDs.__str__ = lambda self: f'"{key_of_value(self)}"'
PivotKeyIDs.__repr__ = lambda self: str(self)

# namedtuple of pivot axis (the level of pivot aggregation) as keys and the ranks as values
RankValue = namedtuple('PivotAxis', "group all")
RankValue.__new__.__defaults__ = (None, None)
RankValue.__str__ = lambda self: f'"rank<{key_of_value(self)}>"'
RankValue.__repr__ = lambda self: str(self)

# namedtuple of pivot axis (the level of pivot aggregation) as keys and the nested pivot-data as values
PivotAxis = namedtuple('PivotAxis', 'in_group in_school')

# namedtuple of count, total sum and average of grades with size of children and rank in pivot-axe
PivotValueAvg = namedtuple('PivotValueAvg', 'count sum avg size rank')
PivotValueAvg.__new__.__defaults__ = (0, 0, None, 0, None)


def grades_by_group_subject_student(session, pivot_axis: PivotAxis = None) -> dict[PivotKeyIDs, PivotValueAvg]:
    """
    :sesion: SQL-Alchemy session
    :pivot_axis: (optional) pivot_axis for partial aggregations (only for debug needs)
    :return: pivot data as a python-dictionary, where each item is a mapping like:
             key - namedtuple of optional student_id, group_id and subject_id as PivotKeyIDs type;
             value - namedtuple count, total sum and average of grades with corresponding rank as PivotValueAvg.
    """
    result_by_subj: dict[PivotKeyIDs, PivotValueAvg] = {}
    sa_avg_grades_by_student_and_subject = (
        select(
            Student.group_id,           # <-- record[0]
            Grade.subject_id,           # <-- record[1]
            Grade.student_id,           # <-- record[2]
            func.count(Grade.grade),    # <-- record[3]
            func.sum(Grade.grade),      # <-- record[4]
            func.avg(Grade.grade))      # <-- record[5]
        .join(Student, Student.id == Grade.student_id)
        .group_by(Grade.student_id, Grade.subject_id)
        .order_by(text("6 desc"))  # <-- SQL-Alchemy ordering by the last column is used to detect the rank
    )

    for record in session.execute(sa_avg_grades_by_student_and_subject).all():
        gr_subj_st_key = PivotKeyIDs(group_id=record[0], subject_id=record[1], student_id=record[2])
        gr_subj_key = PivotKeyIDs(group_id=record[0], subject_id=record[1])
        subj_key = PivotKeyIDs(subject_id=record[1])
        avg_from_db = round(record[5], 2)
        gr_subj_st_value = PivotValueAvg(
            count = record[3],
            sum   = record[4],
            avg   = avg_from_db,
        )
        gr_subj_value = result_by_subj.get(gr_subj_key) or PivotValueAvg()
        gr_subj_value = PivotValueAvg(
            count = gr_subj_value.count + gr_subj_st_value.count,
            sum   = gr_subj_value.sum + gr_subj_st_value.sum,
            size  = gr_subj_value.size + 1,
        )
        subj_value = result_by_subj.get(subj_key) or PivotValueAvg()
        subj_value = PivotValueAvg(
            count = subj_value.count + gr_subj_st_value.count,
            sum   = subj_value.sum + gr_subj_st_value.sum,
            size  = subj_value.size + 1,
        )
        if gr_subj_st_key in result_by_subj:
            print(f"!!! full pivot key already exists: {gr_subj_st_key} !!!", file=sys.stderr)
        ranked_value = PivotValueAvg(
            count = gr_subj_st_value.count,
            sum   = gr_subj_st_value.sum,
            avg = None if gr_subj_st_value.count == 0
                  else round(gr_subj_st_value.sum / float(gr_subj_st_value.count), 2),
            rank=RankValue(group=gr_subj_value.size, all=subj_value.size),
            size=None
        )
        result_by_subj[gr_subj_st_key] = ranked_value
        if ranked_value.avg != avg_from_db:
            print(f"!!! : {ranked_value.avg=} <> {avg_from_db=} !!!", file=sys.stderr)
        result_by_subj[gr_subj_key] = PivotValueAvg(
            count=gr_subj_value.count,
            sum=gr_subj_value.sum,
            avg = None if gr_subj_value.count == 0
                  else round(gr_subj_value.sum / float(gr_subj_value.count), 2),
            size=gr_subj_value.size,
        )
        result_by_subj[subj_key] = PivotValueAvg(
            count=subj_value.count,
            sum=subj_value.sum,
            avg = None if subj_value.count == 0
                  else round(subj_value.sum / float(subj_value.count), 2),
            size=subj_value.size,
        )
        # populating of pivot axis is used just to test and debug values
        if pivot_axis is not None:
            pivot_axis.in_group[gr_subj_key] = result_by_subj[gr_subj_key]
            pivot_axis.in_school[subj_key] = result_by_subj[subj_key]
    return result_by_subj

def grades_by_group_total_student(session, pivot_axis_total: PivotAxis = None) -> dict[PivotKeyIDs, PivotValueAvg]:
    """
    :sesion: SQL-Alchemy session
    :pivot_axis_total: (optional) pivot_axis for partial aggregations (only for debug needs)
    :return: pivot data as a python-dictionary, where each item is a mapping like:
             key - namedtuple of optional student_id, group_id and subject_id as PivotKeyIDs type;
             value - namedtuple count, total sum and average of grades with corresponding rank as PivotValueAvg.
    """
    result_total: dict[PivotKeyIDs, PivotValueAvg] = {}
    sa_avg_grades_by_student_and_subject = (
        select(
            Student.group_id,           # <-- record[0]
            Grade.student_id,           # <-- record[1]
            func.count(Grade.grade),    # <-- record[2]
            func.sum(Grade.grade),      # <-- record[3]
            func.avg(Grade.grade))      # <-- record[4]
        .join(Student, Student.id == Grade.student_id)
        .group_by(Grade.student_id)
        .order_by(text("5 desc"))  # <-- SQL-Alchemy ordering by the last column is used to detect the rank
    )

    school_value = PivotValueAvg()
    for record in session.execute(sa_avg_grades_by_student_and_subject).all():
        gr_st_key = PivotKeyIDs(group_id=record[0], student_id=record[1])
        gr_key = PivotKeyIDs(group_id=record[0])
        avg_from_db = round(record[4], 2)
        gr_st_value = PivotValueAvg(
            count = record[2],
            sum   = record[3],
            avg   = avg_from_db,
        )
        gr_value = result_total.get(gr_key) or PivotValueAvg()
        gr_value = PivotValueAvg(
            count = gr_value.count + gr_st_value.count,
            sum   = gr_value.sum + gr_st_value.sum,
            size  = gr_value.size + 1,
        )
        school_value = PivotValueAvg(
            count = school_value.count + gr_st_value.count,
            sum   = school_value.sum + gr_st_value.sum,
            avg = None if school_value.count == 0
                  else round(school_value.sum / float(school_value.count), 2),
            size  = school_value.size + 1,
        )
        if gr_st_key in result_total:
            print(f"!!! full pivot key already exists: {gr_st_key} !!!", file=sys.stderr)
        ranked_value = PivotValueAvg(
            count = gr_st_value.count,
            sum   = gr_st_value.sum,
            avg = None if gr_st_value.count == 0
                  else round(gr_st_value.sum / float(gr_st_value.count), 2),
            rank=RankValue(group=gr_value.size, all=school_value.size),
            size=None
        )
        result_total[gr_st_key] = ranked_value
        if ranked_value.avg != avg_from_db:
            print(f"!!! : {ranked_value.avg=} <> {avg_from_db=} !!!", file=sys.stderr)
        result_total[gr_key] = PivotValueAvg(
            count=gr_value.count,
            sum=gr_value.sum,
            avg = None if gr_value.count == 0
                  else round(gr_value.sum / float(gr_value.count), 2),
            size=gr_value.size,
        )
        # populating of pivot axis is used just to test and debug values
        if pivot_axis_total is not None:
            pivot_axis_total.in_group[gr_key] = result_total[gr_key]
    result_total[PivotKeyIDs()] = school_value
    if pivot_axis_total is not None:
        pivot_axis_total.in_school[PivotKeyIDs()] = school_value
    return result_total


if __name__ == "__main__":
    from models import DATABASE_URL
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    console = Console(width=160, record=False)
    console.rule("[bold yellow]grades_by_group_subject_student(...):[/]")
    pivot_subj_axis = PivotAxis({},{})
    pivot_subj_data = grades_by_group_subject_student(session, pivot_subj_axis)
    console.print(pivot_subj_data)
    console.rule("pivot_subj_axis", characters="\U0000254C")
    console.print(pivot_subj_axis)

    console.rule("[bold yellow]grades_by_group_total_student(...):[/]")
    pivot_total_axis = PivotAxis({},{})
    pivot_total_data = grades_by_group_total_student(session, pivot_total_axis)
    console.print(pivot_total_data)
    console.rule("pivot_total_axis", characters="\U0000254C")
    console.print(pivot_total_axis)

    console.rule()
    console.print()
    console.end_capture()

    session.close()
    engine.dispose()

