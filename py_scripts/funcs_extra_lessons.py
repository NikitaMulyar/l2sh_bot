import pandas as pd

from py_scripts.funcs_back import prepare_for_markdown, timetable_kbrd
from datetime import datetime
from sqlalchemy_scripts.user_to_extra import Extra_to_User, Extra
from sqlalchemy_scripts.users import User
from py_scripts.consts import days_from_short_text_to_num, days_from_num_to_full_text_formatted, \
    days_from_num_to_full_text, days_from_short_text_to_full
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy_scripts import db_session


def extra_lessons_return(id, button_text):  # Кружки на день для ученика
    day = days_from_short_text_to_full[button_text]
    db_sess = db_session.create_session()
    # extra_lessons = db_sess.query(User).filter(Extra_to_User.user_id == id).all()
    extra_lessons = db_sess.query(User).filter(User.telegram_id == id).first().extra_lessons
    full_text = []
    for extra_lesson in extra_lessons:
        extra = db_sess.query(Extra).filter(Extra.id == extra_lesson.extra_id, Extra.day == day).first()
        if extra:
            text = f"⤵️\n📚 {extra.title} 📚\n"
            text = f"{text}🕝 {extra.time} 🕝\n"
            if extra.teacher.count(".") > 1:
                text = f'{text}Учитель: {extra.teacher}\n'
            place = f"{extra.place} кабинет"
            if "зал" in extra.place or "online" in extra.place:
                place = extra.place
            text = f'{text}🏫 Место проведения: {place} 🏫\n'
            full_text.append(text)
    db_sess.close()
    return "".join(full_text)


def extra_lessons_teachers_return(button_text, surname):  # Кружки на день для учителя
    day = days_from_short_text_to_full[button_text]
    db_sess = db_session.create_session()
    extra_lessons = db_sess.query(Extra).filter(Extra.teacher.like(f'{surname}%'), day == Extra.day).all()
    full_text = []
    extra_was = []
    for extra_lesson in extra_lessons:
        if extra_lesson.title in extra_was:
            continue
        ex = db_sess.query(Extra).filter(Extra.teacher.like(f'{surname}%'), Extra.title == extra_lesson.title,
                                         Extra.time == extra_lesson.time).all()
        classes = []
        for el in ex:
            if str(el.grade) not in classes:
                classes.append(str(el.grade))
        extra_was.append(extra_lesson.title)
        text = f"⤵️\n📚 {extra_lesson.title} ({'/'.join(classes)} класс)📚\n🕝 {extra_lesson.time} 🕝\n"
        place = f"{extra_lesson.place} кабинет"
        if "зал" in extra_lesson.place or "online" in extra_lesson.place:
            place = extra_lesson.place
        text = f'{text}🏫 Место проведения: {place} 🏫\n'
        full_text.append(text)
    db_sess.close()
    return "".join(full_text)


async def extra_lessons_student_by_name(update, button_text, surname, name):  # Кружки на день для ученика по имени
    day = days_from_short_text_to_full[button_text]
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.surname == surname,
                                      User.name == name).first()
    if user:
        extra_lessons = db_sess.query(User).filter(User.surname == surname,
                                                   User.name == name).first().extra_lessons
        full_text = []
        for extra_lesson in extra_lessons:
            extra = db_sess.query(Extra).filter(Extra.id == extra_lesson.extra_id, Extra.day == day).first()
            if extra:
                text = f"⤵️\n📚 {extra.title} 📚\n"
                text = f"{text}🕝 {extra.time} 🕝\n"
                if extra.teacher.count(".") > 1:
                    text = f'{text}Учитель: {extra.teacher}\n'
                place = f"{extra.place} кабинет"
                if "зал" in extra.place or "online" in extra.place:
                    place = extra.place
                text = f'{text}🏫 Место проведения: {place} 🏫\n'
                full_text.append(text)
        text = "".join(full_text)
        if text:
            await update.message.reply_text(text)
    db_sess.close()


async def extra_lessons_for_all_days(update: Update, id, teacher=False, surname=''):
    list_text_res = []
    text_res = ""
    for day, day_number in days_from_short_text_to_num.items():
        if teacher:
            extra_text = extra_lessons_teachers_return(day, surname)
        else:
            extra_text = extra_lessons_return(id, day)
        text = prepare_for_markdown(extra_text)
        if text != "":
            text_res = f'{text_res}_*{days_from_num_to_full_text[day_number]}*_\n{text}\n'
        if len(text_res) > 3000:
            list_text_res.append(text_res)
            text_res = ""
    list_text_res.append(text_res)
    if not list_text_res[0]:
        dont_have_extra = "⚠️ *Вы еще не записывались на кружки*"
        if teacher:
            dont_have_extra = "⚠️ *Вы не проводите кружки*"
        await update.message.reply_text(dont_have_extra, reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
        return
    for el in list_text_res:
        if el:
            await update.message.reply_text(el, reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')


async def extra_send_near(update: Update, context: ContextTypes.DEFAULT_TYPE, flag=False, surname=''):
    today = datetime.now().weekday()
    if context.user_data['NEXT_DAY_TT']:
        today = (today + 1) % 7
    if today == 6:
        today = 0
    days = {value: key for key, value in days_from_short_text_to_num.items()}
    if flag:
        extra_text = extra_lessons_teachers_return(days[today], surname)
    else:
        extra_text = extra_lessons_return(update.message.from_user.id, days[today])
    text = prepare_for_markdown(extra_text)
    have_extra_or_not = f'*Кружки на {days_from_num_to_full_text_formatted[today]}*\n\n{text}'
    if text == '':
        have_extra_or_not = f'*Кружков на {days_from_num_to_full_text_formatted[today]} нет*'
    await update.message.reply_text(have_extra_or_not, parse_mode='MarkdownV2')
    return


async def extra_send_day(update: Update, text__=None, surname=None, flag=False, no_kbrd=False):
    if not text__:
        text__ = update.message.text
    if flag:
        extra_text = extra_lessons_teachers_return(text__, surname)
    else:
        extra_text = extra_lessons_return(update.message.from_user.id, text__)
    text = prepare_for_markdown(extra_text)
    kbrd = None
    if not no_kbrd:
        kbrd = await timetable_kbrd()
    have_extra_or_not = (f'*Кружки на {days_from_num_to_full_text_formatted[days_from_short_text_to_num[text__]]}*'
                         f'\n\n{text}')
    if text == '':
        have_extra_or_not = (f'*Кружков на {days_from_num_to_full_text_formatted[days_from_short_text_to_num[text__]]} '
                             f'нет*')
    await update.message.reply_text(have_extra_or_not, reply_markup=kbrd, parse_mode='MarkdownV2')
    return


async def extract_extra_lessons_from_new_table():
    id_save = []
    db_sess = db_session.create_session()
    for i in range(6):
        extra_lessons = pd.read_excel('data/extra.xlsx', sheet_name=i, usecols=[2, 4, 6, 8, 10, 12]).values
        length = len(extra_lessons)
        for j in range(6):
            k = 1
            while k <= length:
                if not pd.isnull(extra_lessons[k][j]):
                    title = extra_lessons[k][j]
                    time = extra_lessons[k + 1][j]
                    place = extra_lessons[k + 4][j]
                    if "Код" not in extra_lessons[k + 2][j]:
                        teacher = extra_lessons[k + 2][j]
                    else:
                        teacher = extra_lessons[k + 3][j]
                    day = days_from_num_to_full_text[j]
                    teacher = teacher.replace('ё', 'е')
                    extra = Extra(title=title, time=time, day=day, teacher=teacher, place=place, grade=i + 6)
                    try_to_find = db_sess.query(Extra).filter(Extra.title == title, Extra.grade == i + 6,
                                                              Extra.day == day, Extra.time == time).first()
                    if not bool(try_to_find):
                        db_sess.add(extra)
                    else:
                        extra = db_sess.query(Extra).filter(Extra.title == title, Extra.grade == i + 6,
                                                            Extra.day == day).first()
                        extra.teacher = teacher
                        extra.time = time
                        id_save.append(extra.id)
                k += 6
    db_sess.commit()
    db_sess.close()
    await delete_old_extra_lessons(id_save)


async def delete_old_extra_lessons(id_now: list):
    db_sess = db_session.create_session()
    old_extra = db_sess.query(Extra).filter(Extra.id.notin_(id_now)).all()
    for el in old_extra:
        db_sess.delete(el)
    old_extra = db_sess.query(Extra_to_User).filter(Extra_to_User.extra_id.notin_(id_now)).all()
    for el in old_extra:
        db_sess.delete(el)
    db_sess.commit()
    db_sess.close()
