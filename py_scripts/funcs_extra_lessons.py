from py_scripts.funcs_back import db_sess, prepare_for_markdown, timetable_kbrd
import datetime
from sqlalchemy_scripts.user_to_extra import Extra_to_User, Extra
from py_scripts.consts import days_from_short_text_to_num, days_from_num_to_full_text_formatted, days_from_num_to_full_text


def extra_lessons_return(id, button_text):  # Кружки на день для ученика
    days = {"Пн": "Понедельник", "Вт": "Вторник", "Ср": "Среда", "Чт": "Четверг", "Пт": "Пятница", "Сб": "Суббота"}
    day = days[button_text]
    extra_lessons = db_sess.query(Extra_to_User).filter(Extra_to_User.user_id == id).all()
    full_text = []
    for extra_lesson in extra_lessons:
        extra = db_sess.query(Extra).filter(Extra.id == extra_lesson.extra_id, Extra.day == day).first()
        if extra:
            text = "⤵️\n"
            text += f"📚 {extra.title} 📚\n"
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
    days = {"Пн": "Понедельник", "Вт": "Вторник", "Ср": "Среда", "Чт": "Четверг", "Пт": "Пятница", "Сб": "Суббота"}
    day = days[button_text]
    extra_lessons = db_sess.query(Extra).filter(Extra.teacher.like(f'{surname}%'), day == Extra.day).all()
    full_text = []
    extra_was = []
    for extra_lesson in extra_lessons:
        if extra_lesson.title in extra_was:
            continue
        text = "⤵️\n"
        ex = db_sess.query(Extra).filter(Extra.teacher.like(f'{surname}%'), Extra.title == extra_lesson.title,
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


async def extra_lessons_for_all_days(update, id, teacher=False, surname=''):
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
        if teacher:
            await update.message.reply_text(
                f'*Вы не проводите кружки\.*',
                reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(
                f'*Вы еще не записывались на кружки\.*',
                reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
        return
    for el in list_text_res:
        if el:
            await update.message.reply_text(el,
                                            reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')


async def extra_send_near(update, context, flag=False, surname=''):
    today = datetime.datetime.now().weekday()
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
    if text == '':
        await update.message.reply_text(
            f'*Кружков на {days_from_num_to_full_text_formatted[today]} нет*',
            reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
        return
    await update.message.reply_text(
        f'*Кружки на {days_from_num_to_full_text_formatted[today]}*\n\n{text}',
        reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')


async def extra_send_day(update, text__=None, surname=None, flag=False, no_kbrd=False):
    if not text__:
        text__ = update.message.text
    if flag:
        extra_text = extra_lessons_teachers_return(text__, surname)
    else:
        extra_text = extra_lessons_return(update.message.from_user.id, text__)
    text = prepare_for_markdown(extra_text)
    if not no_kbrd:
        if text == '':
            await update.message.reply_text(
                f'*Кружков на {days_from_num_to_full_text_formatted[days_from_short_text_to_num[text__]]} нет*',
                reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
            return
        await update.message.reply_text(
            f'*Кружки на {days_from_num_to_full_text_formatted[days_from_short_text_to_num[text__]]}*\n\n{text}',
            reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
    else:
        if text == '':
            await update.message.reply_text(
                f'*Кружков на {days_from_num_to_full_text_formatted[days_from_short_text_to_num[text__]]} нет*',
                parse_mode='MarkdownV2')
            return
        await update.message.reply_text(
            f'*Кружки на {days_from_num_to_full_text_formatted[days_from_short_text_to_num[text__]]}*\n\n{text}',
            parse_mode='MarkdownV2')
