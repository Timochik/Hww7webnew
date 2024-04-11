""" Text-Reports (styled by Rich and powered by SQL-Alchemy) from students' database """

from typing import Type

from rich.columns import Columns
from rich.console import Console
from rich.table import Table as RichTable

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect, text, select
from sqlalchemy.orm import joinedload

from models import Student, Group, Teacher, Subject, Grade, DATABASE_URL
from pivot import grades_by_group_subject_student, grades_by_group_total_student, PivotKeyIDs, PivotValueAvg

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

inspector = inspect(engine)
print(f"{engine.url = }")
print(f"{engine.driver = }")
print(f"{inspector.get_schema_names() = }")
print(f"{inspector.get_table_names() = }")
print()

with engine.connect() as con:
    for tbl_name in ('groups', 'teachers', 'subjects'):
        print(f"Getting the content of table '{tbl_name}' with raw SQL:")
        sql_query = text(f"SELECT * FROM {tbl_name}")
        print(f"- using the query << {sql_query} >> ")
        print(f"- {[row for row in con.execute(sql_query)]}")
        print("---------------------------")
    print(f"Getting the list of all students with raw SQL:")
    sql_query_students = text("SELECT * FROM students")
    print(f"- using the query for students << {sql_query_students} >> ")
    for student_row in con.execute(sql_query_students):
        print(f"- {student_row};")
print("===========================")
print()

for entity in (Group, Teacher, Subject):
    print(f"- '{entity.__name__}' records via SQL-Alchemy session: {[str(e) for e in session.query(entity).all()]}")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~")

joined_groups = session.query(Group).options(joinedload(Group.students)).all()
print(f"- joined loading groups: {[str(gr) for gr in joined_groups]}")
print("===========================")
print()

console = Console(width=120, record=True)
console.rule("[bold red]Database Structure (tables and columns):[/]")
console.print()

panels = []
for tbl_name in inspector.get_table_names():
    rich_tbl = RichTable(title=f"table [not italic bold blue]'{tbl_name}'[/]")
    rich_tbl.add_column("name")
    rich_tbl.add_column("type")
    for rc in inspector.get_columns(tbl_name):
        rich_tbl.add_row(
            str(rc['name']),
            str(rc['type']),
            style="underline" if rc["primary_key"] == 1 else None
        )
    panels.append(rich_tbl)
console.print(Columns(panels))
console.print()


def query_groups():
    sa_select = (
        select(Group)
        .options(joinedload(Group.students))
    )
    list_groups = [record[0] for record in session.execute(sa_select).unique()]
    rich_tbl = RichTable(
        title=f"query for [not italic bold blue]{Group.__name__}[/]",
        caption=f"{len(list_groups)} records",
    )
    rich_tbl.add_column("Group Name", justify="center")
    rich_tbl.add_column("Group Size", justify="right")
    for gr in list_groups:
        rich_tbl.add_row(
            f"[bold yellow]{gr.name}[/]",
            str(len(gr.students))
        )
    return rich_tbl


def query_subjects():
    sa_select = (
        select(Subject).order_by(Subject.name)
        .options(joinedload(Subject.teacher))
    )
    list_subjects = [record[0] for record in session.execute(sa_select).unique()]
    rich_tbl = RichTable(
        title=f"query for [not italic bold blue]{Subject.__name__}[/]",
        caption=f"{len(list_subjects)} records",
    )
    rich_tbl.add_column("Subject", justify="center")
    rich_tbl.add_column("Teacher Name", justify="left")
    for sbj in list_subjects:
        rich_tbl.add_row(
            sbj.name,
            sbj.teacher.name
        )
    return rich_tbl


def query_teachers():
    sa_select = (
        select(Teacher).order_by(Teacher.name)
        .options(joinedload(Teacher.subjects))
    )
    list_teachers = [record[0] for record in session.execute(sa_select).unique()]
    rich_tbl = RichTable(
        title=f"query for [not italic bold blue]{Teacher.__name__}[/]",
        caption=f"{len(list_teachers)} records",
    )
    rich_tbl.add_column("Teacher Name", justify="left")
    rich_tbl.add_column("Subjects", justify="left")
    for tch in list_teachers:
        rich_tbl.add_row(
            tch.name,
            ", ".join([sbj.name for sbj in tch.subjects])
        )
    return rich_tbl


console.rule("[bold red]Persistent Data (small result-sets):[/]")
console.print()
console.print(Columns([
    query_groups(),
    query_subjects(),
    query_teachers()
]))
console.print()

def style_avg(rank: int, highlight_color: str):
    if rank == 1:
        return f"bold {highlight_color}"
    elif rank <= 3:
        return f"{highlight_color}"
    else:
        return "default"
style_avg_in_group = lambda rank: style_avg(rank, "yellow")
style_avg_all = lambda rank: style_avg(rank, "red")

def rank_formatted(rank: int, highlight_color: str):
    if rank <= 3:
        return f"[{style_avg(rank,highlight_color)}]({rank})[/]"
    else:
        return f"[italic]{rank}[/]"
rank_fmt_in_group = lambda rank: rank_formatted(rank, "yellow")
rank_fmt_all = lambda rank: rank_formatted(rank, "red")

def query_avg_by_group(gr: Type[Group],
                       pivot_by_subj: dict[PivotKeyIDs, PivotValueAvg],
                       pivot_total: dict[PivotKeyIDs, PivotValueAvg]):
    group_id = gr.id
    group_name = gr.name

    sa_select_subjects = (
        select(Subject).order_by(Subject.name)
        .options(joinedload(Subject.teacher))
    )
    list_subjects = [record[0] for record in session.execute(sa_select_subjects).unique()]
    sa_select_students = (
        select(Student)
        .where(Student.group_id == group_id)
        .order_by(Student.name)
    )
    list_students = [record[0] for record in session.execute(sa_select_students).all()]

    rich_tbl = RichTable(
        title=f"query for AVERAGE([not italic bold blue]{Grade.__name__}[/]) "
              f"and RANK " +
              #f"and RANK (\U0001F947) " +  # <-- a medal unicode-symbol
              f"of each [not italic bold blue]{Student.__name__}[/] " +
              f"in group [not italic bold yellow]'{group_name}'[/]")
    rich_tbl.add_column("#", justify="right")
    rich_tbl.add_column("Name", justify="left")
    rich_tbl.add_column("rnk", justify="center")
    # rich_tbl.add_column("\U0001F947", justify="center", style="italic")  # <-- a medal unicode-symbol
    for sbj in list_subjects:
        rich_tbl.add_column(f"{sbj.name}", justify="right", max_width=6, min_width=6)
    rich_tbl.add_column("TOTAL", justify="right", style="bold", max_width=6, min_width=6)
    rich_tbl.add_column("#", justify="right")
    for order_num, st in enumerate(list_students):
        row_data = []
        order_num_str = f"[dim]{order_num + 1}[/]"
        row_data.append(order_num_str)
        row_data.append(st.name)
        pivot_total_key = PivotKeyIDs(group_id=group_id, student_id=st.id)
        pivot_total_value: PivotValueAvg = pivot_total[pivot_total_key]
        rank_total_value = pivot_total_value.rank
        row_data.append(rank_fmt_in_group(rank_total_value.group))
        for subj in list_subjects:
            pivot_by_subj_key = PivotKeyIDs(subject_id=subj.id, group_id=group_id, student_id=st.id)
            pivot_by_subj_value: PivotValueAvg = pivot_by_subj[pivot_by_subj_key]
            rank_by_subj_value = pivot_by_subj_value.rank
            avg_by_subj = pivot_by_subj_value.avg
            style_by_subj_avg = style_avg_in_group(rank_by_subj_value.group)
            row_data.append(f"[{style_by_subj_avg}]{avg_by_subj:5.2f}[/]")
        avg_total = pivot_total_value.avg
        style_total_avg = style_avg_in_group(rank_total_value.group)
        row_data.append(f"[{style_total_avg}]{avg_total:5.2f}[/]")
        row_data.append(order_num_str)
        rich_tbl.add_row(*row_data, end_section=(order_num + 1 == len(list_students)))
    summary_data = []
    summary_data.append("")
    summary_data.append("[bold]the whole group[/bold]")
    summary_data.append("")
    for subj in list_subjects:
        pivot_key = PivotKeyIDs(subject_id=subj.id, group_id=group_id)
        summary_data.append(f"{pivot_data_subj[pivot_key].avg:5.2f}")
    pivot_total_gr_key = PivotKeyIDs(group_id=group_id)
    pivot_total_gr_value: PivotValueAvg = pivot_total[pivot_total_gr_key]
    summary_data.append(f"[bold]{pivot_total_gr_value.avg}[/bold]")
    summary_data.append("")
    rich_tbl.add_row(*summary_data)
    return rich_tbl


def query_avg_in_school(pivot_by_subj: dict[PivotKeyIDs, PivotValueAvg], pivot_total: dict[PivotKeyIDs, PivotValueAvg]):
    sa_select_subjects = (
        select(Subject).order_by(Subject.name)
        .options(joinedload(Subject.teacher))
    )
    list_subjects = [record[0] for record in session.execute(sa_select_subjects).unique()]
    sa_select_students = (
        select(Student)
        .order_by(Student.name)
        .options(joinedload(Student.group))
    )
    list_students = [record[0] for record in session.execute(sa_select_students).all()]

    rich_tbl = RichTable(
        title=f"query for AVERAGE([not italic bold blue]{Grade.__name__}[/]) "
              f"and RANK " +
              #f"and RANK (\U0001F947) " +  # <-- a medal unicode-symbol
              f"of each [not italic bold blue]{Student.__name__}[/] in [bold red]all groups[/]")
    rich_tbl.add_column("#", justify="right")
    rich_tbl.add_column("Name", justify="left")
    rich_tbl.add_column("rnk", justify="center")
    # rich_tbl.add_column("\U0001F947", justify="center", style="italic")  # <-- a medal unicode-symbol
    for sbj in list_subjects:
        rich_tbl.add_column(f"{sbj.name}", justify="right", max_width=6, min_width=6)
    rich_tbl.add_column("TOTAL", justify="right", style="bold", max_width=6, min_width=6)
    rich_tbl.add_column("gr", justify="center")
    for order_num, st in enumerate(list_students):
        row_data = []
        order_num_str = f"[dim]{order_num + 1}[/]"
        row_data.append(order_num_str)
        row_data.append(st.name)
        pivot_total_key = PivotKeyIDs(group_id=st.group_id, student_id=st.id)
        pivot_total_value: PivotValueAvg = pivot_total[pivot_total_key]
        rank_total_value = pivot_total_value.rank
        row_data.append(rank_fmt_all(rank_total_value.all))
        for subj in list_subjects:
            pivot_by_subj_key = PivotKeyIDs(subject_id=subj.id, group_id=st.group_id, student_id=st.id)
            pivot_by_subj_value: PivotValueAvg = pivot_by_subj[pivot_by_subj_key]
            rank_by_subj_value = pivot_by_subj_value.rank
            avg_by_subj = pivot_by_subj_value.avg
            style_by_subj_avg = style_avg_all(rank_by_subj_value.all)
            row_data.append(f"[{style_by_subj_avg}]{avg_by_subj:5.2f}[/]")
        avg_total = pivot_total_value.avg
        style_total_avg = style_avg_all(rank_total_value.all)
        row_data.append(f"[{style_total_avg}]{avg_total:5.2f}[/]")
        row_data.append(f"[yellow]#{st.group_id}[/]")
        rich_tbl.add_row(*row_data, end_section=(order_num + 1 == len(list_students)))
    summary_data = []
    summary_data.append("")
    summary_data.append("[bold]the whole school[/bold]")
    summary_data.append("")
    for subj in list_subjects:
        pivot_key = PivotKeyIDs(subject_id=subj.id)
        summary_data.append(f"{pivot_data_subj[pivot_key].avg:5.2f}")
    pivot_total_value: PivotValueAvg = pivot_total[PivotKeyIDs()]
    summary_data.append(f"[bold]{pivot_total_value.avg}[/bold]")
    summary_data.append("")
    rich_tbl.add_row(*summary_data)
    return rich_tbl


# most of data-complexity is in python-module 'pivot.py':
print("... calculating pivot-data per subject: ...")
pivot_data_subj = grades_by_group_subject_student(session)
print("... calculating pivot-data for all subject: ...")
pivot_data_total = grades_by_group_total_student(session)

console.rule("[bold red]Persistent Data per each group (grades of students in subjects):[/]")
console.print()
console.print(query_avg_by_group(joined_groups[0], pivot_data_subj, pivot_data_total))
console.rule(characters="\U0000254C")
console.print(query_avg_by_group(joined_groups[1], pivot_data_subj, pivot_data_total))
console.rule(characters="\U0000254C")
console.print(query_avg_by_group(joined_groups[2], pivot_data_subj, pivot_data_total))
console.print()
#console.print("[italic magenta] ... to be done ... [/]", justify="center")

console.rule("[bold red]Persistent Data for all groups (grades of students in subjects):[/]")
console.print()
console.print(query_avg_in_school(pivot_data_subj, pivot_data_total))
console.rule()
console.print()
console.end_capture()

from pathlib import Path
from rich import terminal_theme as rich_term

current_script_path: Path = Path(__file__)
export_path = current_script_path.parent / "export"
export_svg_path = export_path / "svg"
export_html_path = export_path / "html"
export_svg_path.mkdir(parents=True, exist_ok=True)
export_html_path.mkdir(parents=True, exist_ok=True)
export_stem = current_script_path.stem

DICT_TERM_THEME = {
    "default": rich_term.DEFAULT_TERMINAL_THEME,
    "dimmed": rich_term.DIMMED_MONOKAI,
    "monokai": rich_term.MONOKAI,
    "night": rich_term.NIGHT_OWLISH,
    "export": rich_term.SVG_EXPORT_THEME,
}
for (theme_suffix, theme) in DICT_TERM_THEME.items():
    svg_file_path = export_svg_path / f"{export_stem}--{theme_suffix}.svg"
    save_svg_title = f"results of 'seed.py' in SVG-format - for '{theme_suffix}' theme"
    console.save_svg(str(svg_file_path), title=save_svg_title, clear=False, theme=theme)
    print(f"output is captured and saved in '{svg_file_path}' as SVG")
print()
for (theme_suffix, theme) in DICT_TERM_THEME.items():
    html_file_path = export_html_path / f"{export_stem}--{theme_suffix}.html"
    console.save_html(str(html_file_path), clear=False, theme=theme)
    print(f"output is captured and saved in '{html_file_path}' as HTML")
print()

session.close()
engine.dispose()
