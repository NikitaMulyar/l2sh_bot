# -*- coding: utf-8 -*-
from funcs_back import *


days = {0: 'Понедельник', 1: 'Вторник', 2: 'Среда', 3: 'Четверг', 4: 'Пятница', 5: 'Суббота'}


async def extract_timetable_for_teachers():
    def get_all_teachers():
        reader = PyPDF2.PdfReader(f"{path_to_timetables}teachers.pdf")
        i = -1
        for page in reader.pages:
            i += 1
            info = page.extract_text().split('\n')[-1].split()
            info[2] = info[2][0]
            yield " ".join(info[1:3]), i

    async def save_timetable_csv(full_name, page_n):
        with pdfplumber.open(f"{path_to_timetables}teachers.pdf") as pdf:
            page = pdf.pages[page_n]
            table = page.extract_table()
            df = pd.DataFrame(table[1:], columns=table[0])
            for col in df.columns.values:
                df.loc[df[col] == '', col] = '--'
            df.ffill(axis=0, inplace=True)
            df.to_csv(path_to_timetables_csv + f'{full_name}.csv')

    for teacher, page_n in list(get_all_teachers()):
        await save_timetable_csv(teacher, page_n)


async def get_timetable_for_teacher(context, full_name):
    if not os.path.exists(path_to_timetables_csv + f'{full_name}.csv'):
        return pd.DataFrame(), -1
    now_ = datetime.now()
    day = now_.weekday()
    if day == 6:
        timetable_, day = await extract_teacher_timetable_for_day(0, full_name)
        context.user_data['NEXT_DAY_TT'] = True
        return timetable_, 0
    timetable_, day = await extract_teacher_timetable_for_day(day, full_name)
    if timetable_.empty:
        return timetable_, day
    last_les_end_h, last_les_end_m = map(int,
                                         timetable_.index.values[-1].split(' - ')[-1]
                                         .split(':'))
    h, m = now_.hour, now_.minute
    if (h, m) > (last_les_end_h, last_les_end_m):
        context.user_data['NEXT_DAY_TT'] = True
        if day == 5:
            timetable_, day = await extract_teacher_timetable_for_day(0, full_name)
            return timetable_, 0
        timetable_, day = await extract_teacher_timetable_for_day(day + 1, full_name)
        # Флажок, чтобы расписание на следующий день не выделялось, если завтра больше уроков
    else:
        context.user_data['NEXT_DAY_TT'] = False
    return timetable_, day


async def get_standard_timetable_for_teacher(full_name, day):
    if not os.path.exists(path_to_timetables_csv + f'{full_name}.csv'):
        return pd.DataFrame(), -1
    timetable_, day = await extract_teacher_timetable_for_day(day, full_name)
    return timetable_, day


async def extract_teacher_timetable_for_day(day, full_name):
    df = pd.read_csv(path_to_timetables_csv + f'{full_name}.csv')
    df.drop('Unnamed: 0', axis=1, inplace=True)
    day2 = days[day]
    df = df[['Unnamed: 1', day2]]
    df = df[df[day2] != '--']
    df = df.set_index(df['Unnamed: 1'].values)
    return df, day


def extra_lessons_teachers_return(id, button_text):
    days = {"Пн": "Понедельник", "Вт": "Вторник", "Ср": "Среда", "Чт": "Четверг", "Пт": "Пятница", "Сб": "Суббота"}
    day = days[button_text]
    user = db_sess.query(User).filter(User.telegram_id == id).first()
    extra_lessons = db_sess.query(Extra).filter(Extra.teacher.like(f'{user.surname}%'), day == Extra.day).all()
    full_text = []
    extra_was = []
    for extra_lesson in extra_lessons:
        if extra_lesson.title in extra_was:
            continue
        text = "⤵️\n"
        ex = db_sess.query(Extra).filter(Extra.teacher.like(f'{user.surname}%'), Extra.title == extra_lesson.title,
                                         Extra.time == extra_lesson.time).all()
        classes = []
        for el in ex:
            if str(el.grade) not in classes:
                classes.append(str(el.grade))
        extra_was.append(extra_lesson.title)
        text += f"📚 {extra_lesson.title} ({'/'.join(classes)} класс)📚\n"
        text += f"🕝 {extra_lesson.time} 🕝\n"
        place = ""
        if "зал" in extra_lesson.place or "online" in extra_lesson.place:
            place = extra_lesson.place
        else:
            place = f"{extra_lesson.place} кабинет"
        text += f'🏫 Место проведения: {place} 🏫\n'
        full_text.append(text)
    return "".join(full_text)