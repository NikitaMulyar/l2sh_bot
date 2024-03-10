from py_scripts.funcs_extra_lessons import extra_lessons_for_all_days, extra_send_day, extra_send_near
from py_scripts.funcs_back import (throttle, extra_school_timetable_kbrd,
                                   timetable_kbrd, check_busy, intensive_kbrd, get_intensive)
from py_scripts.funcs_teachers import timetable_teacher_for_each_day
from datetime import datetime
from sqlalchemy_scripts.users import User
from py_scripts.consts import days_from_short_text_to_num
from py_scripts.funcs_students import get_nearest_timetable_with_edits_for_student
from py_scripts.funcs_students import get_standard_timetable_with_edits_for_student
from py_scripts.funcs_teachers import get_standard_timetable_with_edits_for_teacher
from telegram.ext import ContextTypes
from telegram import Update
from sqlalchemy_scripts import db_session


class GetTimetable:
    @throttle()
    async def get_timetable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context, flag=True)
        if is_busy:
            return
        chat_id = update.message.chat_id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            db_sess.close()
            await update.message.reply_text('⚠️ *Для начала заполните свои данные\: \/start*',
                                            parse_mode='MarkdownV2')
            return
        if update.message.text == '🎨Мои кружки🎨':
            await update.message.reply_text('Выберите интересующий Вас день',
                                            reply_markup=await extra_school_timetable_kbrd())
            context.user_data['EXTRA_CLICKED'] = True
        elif update.message.text == '⚡️Интенсивы⚡️':
            await update.message.reply_text('Выберите интересующий Вас предмет',
                                            reply_markup=await intensive_kbrd())
            context.user_data['EXTRA_CLICKED2'] = True
        elif context.user_data.get('EXTRA_CLICKED2'):
            context.user_data['EXTRA_CLICKED2'] = False
            if user.role == 'teacher' or user.role == 'admin':
                text_inten = await get_intensive(update.message.text, teacher=True, name=user.name, surname=user.surname)
            else:
                text_inten = await get_intensive(update.message.text, parallel=user.number)
            await update.message.reply_text(text_inten, reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
        elif user.role == 'teacher' or user.role == 'admin':
            if update.message.text == '📚Ближайшее расписание📚':
                context.user_data['NEXT_DAY_TT'] = False
                await timetable_teacher_for_each_day(update, context, user)
                await extra_send_near(update, context, flag=True, surname=user.surname)
            elif (not context.user_data.get('EXTRA_CLICKED') and
                  update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']):
                t = await get_standard_timetable_with_edits_for_teacher(update.message.text,
                                                                        user.name, user.surname,
                                                                        flag=False)
                if len(t) == 1:
                    await update.message.reply_text(t[0], parse_mode='MarkdownV2')
                else:
                    total_len = len(t[0])
                    ind = 0
                    while ind < len(t[1]) and total_len + len(t[1][ind]) < 4000:
                        total_len += len(t[1][ind])
                        ind += 1
                    await update.message.reply_text(t[0] + "".join(t[1][:ind]),
                                                    parse_mode='MarkdownV2')
                    scnd = "".join(t[1][ind:])
                    if scnd:
                        await update.message.reply_text(scnd, parse_mode='MarkdownV2')
                await extra_send_day(update, flag=True, surname=user.surname, no_kbrd=True)
            elif context.user_data.get('EXTRA_CLICKED') and update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']:
                context.user_data['EXTRA_CLICKED'] = False
                await extra_send_day(update, flag=True, surname=user.surname)
            elif update.message.text == '♟️Сегодня♟️':
                today = datetime.now().weekday()
                context.user_data['EXTRA_CLICKED'] = False
                if today == 6:
                    await update.message.reply_text(f'*В воскресенье нужно отдыхать\! Кружков нет\.*',
                                                    reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
                    return
                days = {value: key for key, value in days_from_short_text_to_num.items()}
                await extra_send_day(update, text__=days[today], flag=True, surname=user.surname)
            elif update.message.text == '🎭Все кружки🎭':
                context.user_data['EXTRA_CLICKED'] = False
                await extra_lessons_for_all_days(update, update.message.from_user.id, teacher=True,
                                                 surname=user.surname)
        else:
            if update.message.text == '📚Ближайшее расписание📚':
                context.user_data['NEXT_DAY_TT'] = False
                await get_nearest_timetable_with_edits_for_student(update, context, user)
                await extra_send_near(update, context)
            elif (not context.user_data.get('EXTRA_CLICKED') and
                  update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']):
                t = await get_standard_timetable_with_edits_for_student(update.message.text,
                                                                        user.grade, user.name,
                                                                        user.surname, flag=False)
                if len(t) == 1:
                    await update.message.reply_text(t[0], parse_mode='MarkdownV2')
                else:
                    total_len = len(t[0])
                    ind = 0
                    while ind < len(t[1]) and total_len + len(t[1][ind]) < 4000:
                        total_len += len(t[1][ind])
                        ind += 1
                    await update.message.reply_text(t[0] + "".join(t[1][:ind]),
                                                    parse_mode='MarkdownV2')
                    scnd = "".join(t[1][ind:])
                    if scnd:
                        await update.message.reply_text(scnd, parse_mode='MarkdownV2')
                await extra_send_day(update, no_kbrd=True)
            elif context.user_data.get('EXTRA_CLICKED') and update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']:
                context.user_data['EXTRA_CLICKED'] = False
                await extra_send_day(update)
            elif update.message.text == '♟️Сегодня♟️':
                today = datetime.now().weekday()
                context.user_data['EXTRA_CLICKED'] = False
                if today == 6:
                    await update.message.reply_text(f'*В воскресенье нужно отдыхать\! Кружков нет\.*',
                                                    reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
                    return
                days = {value: key for key, value in days_from_short_text_to_num.items()}
                await extra_send_day(update, text__=days[today])
            elif update.message.text == '🎭Все кружки🎭':
                context.user_data['EXTRA_CLICKED'] = False
                await extra_lessons_for_all_days(update, update.message.from_user.id)
        db_sess.close()
