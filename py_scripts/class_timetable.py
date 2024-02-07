import os
from py_scripts.funcs_extra_lessons import extra_lessons_for_all_days, extra_send_day, extra_send_near
from py_scripts.consts import path_to_timetables_csv, days_from_num_to_full_text_formatted
from py_scripts.funcs_back import (throttle, extra_school_timetable_kbrd, prepare_for_markdown,
                                   db_sess, timetable_kbrd, check_busy, intensive_kbrd, get_intensive)
from py_scripts.funcs_students import get_timetable_for_user, get_timetable_for_user_6_9
from py_scripts.funcs_teachers import timetable_teacher_for_each_day
from datetime import datetime
from sqlalchemy_scripts.users import User
from py_scripts.consts import days_from_short_text_to_num, lessons_keys, for_datetime
from py_scripts.funcs_students import get_edits_for_student
from py_scripts.funcs_students import get_standard_timetable_with_edits_for_student
from py_scripts.funcs_teachers import get_standard_timetable_with_edits_for_teacher
from telegram.ext import ContextTypes
from telegram import Update


class GetTimetable:
    @throttle()
    async def get_timetable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context, flag=True)
        if is_busy:
            return
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            await update.message.reply_text(f'⚠️Для начала заполните свои данные: /start')
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
                if (user.role == 'admin' or user.role == 'teacher') and not os.path.exists(
                        path_to_timetables_csv + f'{user.surname} {user.name[0]}.csv'):
                    await update.message.reply_text(f'⚠️У вас нет личного расписания')
                    return
                context.user_data['NEXT_DAY_TT'] = False
                await timetable_teacher_for_each_day(update, context, user)
                await extra_send_near(update, context, flag=True, surname=user.surname)
            elif (not context.user_data.get('EXTRA_CLICKED') and
                  update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']):
                if (user.role == 'admin' or user.role == 'teacher') and not os.path.exists(
                        path_to_timetables_csv + f'{user.surname} {user.name[0]}.csv'):
                    await update.message.reply_text(f'⚠️У вас нет личного расписания')
                    return
                t = await get_standard_timetable_with_edits_for_teacher(context,
                                                                        update.message.text,
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
                if int(user.number) >= 10:
                    lessons, day = await get_timetable_for_user(context, f'{user.surname} {user.name}', user.grade)
                else:
                    lessons, day = await get_timetable_for_user_6_9(context, user.grade)
                if lessons.empty:
                    txt = prepare_for_markdown(user.surname + ' ' + user.name + ' ' + user.grade)
                    class_txt = user.grade

                    await update.message.reply_text(f'Ученика "{txt}" не найдено или отсутствует '
                                                    f'расписание для {class_txt} класса.')
                    return
                title = f'*Расписание на _{days_from_num_to_full_text_formatted[day]}_*\n\n'
                t = ""
                time_now = datetime.now()  # - timedelta(hours=3)
                # !!!!!!!!!!!!!!!!!
                for txt_info, key in lessons_keys.items():
                    try:
                        if int(user.number) >= 10:
                            pre_lesson_info = lessons.loc[key].split('###')
                        else:
                            pre_lesson_info = lessons.loc[key][day].split('###')
                        start, end = for_datetime[key]
                        # Получили информацию об уроке: учитель, предмет, каб.
                        if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                            t += f'_*' + prepare_for_markdown(f'➡️ {txt_info}')
                        else:
                            t += prepare_for_markdown(f'{txt_info}')
                        last_cab = ''
                        for lesson_info in pre_lesson_info:
                            lesson_info = lesson_info.split('\n')
                            lesson_info[-2] = lesson_info[-2].strip()
                            if lesson_info[-2] not in ['вероятностей', 'практикум (1)', 'Час', 'структуры данных (1)',
                                                       'программирование (1)', 'практикум (2)', 'структуры данных (2)',
                                                       'программирование (2)',
                                                       'математика (1)', '(1)', 'физика (1)', 'эффекты (1)',
                                                       'математика (2)', 'математике']:
                                if 'Эрлих И.Г.' in lesson_info[-1]:
                                    lesson_info = ['Эрлих И.Г.'] + [lesson_info[-2]] + [lesson_info[-1].split(' ')[-1]]
                                lesson_name = lesson_info[-2]
                                teachers = " ".join(lesson_info[:-2])
                            else:
                                if 'Эрлих И.Г.' in lesson_info[-1]:
                                    lesson_info = ['Эрлих И.Г.'] + lesson_info[-3:-1] + [lesson_info[-1].split(' ')[-1]]
                                lesson_name = " ".join(lesson_info[-3:-1])
                                teachers = " ".join(lesson_info[:-3])
                            cabinet = lesson_info[-1]
                            if 'В' in lesson_name and 'Т' in lesson_name and 'Э.' in lesson_name and 'К.' in lesson_name or \
                                    'В' in lesson_name and 'Т.' in lesson_name and 'Э.' in lesson_name and 'К' in lesson_name:
                                one_more_teacher_VTEK = (lesson_name.replace('В', '').replace('Т', '').
                                                         replace('Э.', '.').replace('К.', '.').replace('Т.', '.'))
                                cnt = sum([int(i in 'АБВГДЕËЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ') for i in
                                           one_more_teacher_VTEK])
                                if cnt > 3:
                                    one_more_teacher_VTEK = one_more_teacher_VTEK[:-1]
                                teachers += " " + one_more_teacher_VTEK
                                lesson_name = 'ВТЭК'
                            elif lesson_name == 'И.Н. ВТЭК':
                                lesson_name = 'ВТЭК'
                                teachers += " И.Н."
                            if len(lesson_info) == 2:
                                cabinet = last_cab
                                lesson_name = lesson_info[-1]
                                teachers = lesson_info[0]
                            t += prepare_for_markdown(
                                f'{lesson_name} - каб. {cabinet}\n(учитель: {teachers})\n')
                            last_cab = cabinet
                        if start <= (time_now.hour, time_now.minute) < end and not context.user_data['NEXT_DAY_TT']:
                            t += '*_'
                        t += '\n'
                    except Exception as e:
                        continue
                t += '\n'
                edits_text = await get_edits_for_student(context, user.grade)
                ind = None
                if edits_text:
                    t = title + '_' + prepare_for_markdown(
                        '⚠️Обратите внимание, что для Вашего класса ниже есть изменения в расписании!') + '_\n\n' + t
                    total_len = len(t)
                    ind = 0
                    while ind < len(edits_text) and total_len + len(edits_text[ind]) < 4000:
                        total_len += len(edits_text[ind])
                        ind += 1
                    await update.message.reply_text(t + "".join(edits_text[:ind]), parse_mode='MarkdownV2')
                    scnd = "".join(edits_text[ind:])
                    if scnd:
                        await update.message.reply_text(scnd, parse_mode='MarkdownV2')
                else:
                    t = title + '\n' + t
                    await update.message.reply_text(t, parse_mode='MarkdownV2')
                await extra_send_near(update, context)
            elif (not context.user_data.get('EXTRA_CLICKED') and
                  update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']):
                t = await get_standard_timetable_with_edits_for_student(context, update.message.text,
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
