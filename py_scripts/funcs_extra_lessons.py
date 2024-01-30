from py_scripts.funcs_back import db_sess, prepare_for_markdown, timetable_kbrd
from datetime import datetime
from sqlalchemy_scripts.user_to_extra import Extra_to_User, Extra
from py_scripts.consts import days_from_short_text_to_num, days_from_num_to_full_text_formatted, \
    days_from_num_to_full_text, days_from_short_text_to_full
from telegram import Update
from telegram.ext import ContextTypes


def extra_lessons_return(id, button_text):  # Кружки на день для ученика
    day = days_from_short_text_to_full[button_text]
    extra_lessons = db_sess.query(Extra_to_User).filter(Extra_to_User.user_id == id).all()
    full_text = []
    for extra_lesson in extra_lessons:
        extra = db_sess.query(Extra).filter(Extra.id == extra_lesson.extra_id, Extra.day == day).first()
        if extra:
            text = f"⤵️\n📚 {extra.title} 📚\n"
            text += f"🕝 {extra.time} 🕝\n"
            if extra.teacher.count(".") > 1:
                text += f'Учитель: {extra.teacher}\n'
            place = f"{extra.place} кабинет"
            if "зал" in extra.place or "online" in extra.place:
                place = extra.place
            text += f'🏫 Место проведения: {place} 🏫\n'
            full_text.append(text)
    return "".join(full_text)


def extra_lessons_teachers_return(button_text, surname):  # Кружки на день для учителя
    day = days_from_short_text_to_full[button_text]
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
        text = f"⤵️\n📚 {extra_lesson.title} ({'/'.join(classes)} класс)📚\n"
        text += f"🕝 {extra_lesson.time} 🕝\n"
        place = f"{extra_lesson.place} кабинет"
        if "зал" in extra_lesson.place or "online" in extra_lesson.place:
            place = extra_lesson.place
        text += f'🏫 Место проведения: {place} 🏫\n'
        full_text.append(text)
    return "".join(full_text)


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
            text_res += f'_*{days_from_num_to_full_text[day_number]}*_\n{text}\n'
        if len(text_res) > 3000:
            list_text_res.append(text_res)
            text_res = ""
    list_text_res.append(text_res)
    if not list_text_res[0]:
        dont_have_extra = "*Вы еще не записывались на кружки\.*"
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
