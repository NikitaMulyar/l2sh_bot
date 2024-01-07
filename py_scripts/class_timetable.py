import os
from telegram.ext import ConversationHandler

from py_scripts.class_extra_lesson import extra_lessons_for_each_day, extra_lessons_for_all_days, extra_send_day
from py_scripts.consts import path_to_timetables_csv, days_from_num_to_full_text_formatted
from py_scripts.funcs_back import get_edits_in_timetable, throttle, extra_school_timetable_kbrd, get_timetable_for_user, \
    get_timetable_for_user_6_9, get_standard_timetable_for_user, get_standard_timetable_for_user_6_9, \
    prepare_for_markdown, db_sess, timetable_kbrd
from py_scripts.funcs_teachers import extra_send_near, timetable_teacher_for_each_day
from datetime import datetime
from sqlalchemy_scripts.users import User
from py_scripts.consts import days_from_num_to_full_text, days_from_short_text_to_num, lessons_keys, for_datetime
from py_scripts.timetable_back_funcs import create_list_of_edits_lessons_for_student, get_edits_for_student
from py_scripts.timetable_back_funcs import create_list_of_edits_lessons_for_teacher, get_edits_for_teacher


class GetTimetable:
    @throttle
    async def get_timetable(self, update, context):
        if context.user_data.get('in_conversation'):
            return
        chat_id = update.message.chat.id
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if not user:
            await update.message.reply_text(f'⚠️Для начала заполните свои данные: /start')
            return
        if (user.role == 'admin' or user.role == 'teacher') and not os.path.exists(
                path_to_timetables_csv + f'{user.surname} {user.name[0]}.csv'):
            await update.message.reply_text(f'⚠️У вас нет личного расписания')
            return
        elif update.message.text == '🎨Мои кружки🎨':
            await update.message.reply_text('Выберите интересующий Вас день',
                                            reply_markup=await extra_school_timetable_kbrd())
            context.user_data['EXTRA_CLICKED'] = True
        elif user.role == 'teacher' or user.role == 'admin':
            if update.message.text == '📚Ближайшее расписание📚':
                context.user_data['NEXT_DAY_TT'] = False
                edits_text = await get_edits_for_teacher(context, user.surname, user.name)
                await timetable_teacher_for_each_day(context, user, update, edits_text, near=True)
            elif (not context.user_data.get('EXTRA_CLICKED') and
                  update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']):
                edits_text = ""
                context.user_data['NEXT_DAY_TT'] = False
                if days_from_short_text_to_num[update.message.text] == 0 and datetime.now().weekday() == 5:
                    context.user_data['NEXT_DAY_TT'] = True
                    edits_text = await get_edits_for_teacher(context, user.surname, user.name)
                elif days_from_short_text_to_num[update.message.text] == datetime.now().weekday():
                    context.user_data['NEXT_DAY_TT'] = False
                    edits_text = await get_edits_for_teacher(context, user.surname, user.name)
                elif days_from_short_text_to_num[update.message.text] == (datetime.now().weekday() + 1) % 7:
                    context.user_data['NEXT_DAY_TT'] = True
                    edits_text = await get_edits_for_teacher(context, user.surname, user.name)
                await timetable_teacher_for_each_day(context, user, update, edits_text)
            elif context.user_data.get('EXTRA_CLICKED') and update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']:
                context.user_data['EXTRA_CLICKED'] = False
                await extra_lessons_for_each_day(update, update.message.from_user.id, update.message.text,
                                                 teacher=True)
            elif update.message.text == '♟️Сегодня♟️':
                today = datetime.now().weekday()
                context.user_data['EXTRA_CLICKED'] = False
                if today == 6:
                    await update.message.reply_text(f'*В воскресенье нужно отдыхать\! Кружков нет\.*',
                                                    reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
                    return
                days = {value: key for key, value in days_from_short_text_to_num.items()}
                await extra_lessons_for_each_day(update, update.message.from_user.id, days[today], teacher=True)
            elif update.message.text == '🎭Все кружки🎭':
                context.user_data['EXTRA_CLICKED'] = False
                await extra_lessons_for_all_days(update, update.message.from_user.id, teacher=True)
        else:
            if update.message.text == '📚Ближайшее расписание📚':
                context.user_data['NEXT_DAY_TT'] = False
                if int(user.number) >= 10:
                    lessons, day = await get_timetable_for_user(context, f'{user.surname} {user.name}', user.grade)
                else:
                    lessons, day = await get_timetable_for_user_6_9(context, user.grade)
                if lessons.empty:
                    txt = (user.surname + ' ' + user.name + ' ' + user.grade)
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
                if edits_text:
                    t = title + '_' + prepare_for_markdown(
                        '⚠️Обратите внимание, что для Вашего класса ниже есть изменения в расписании!\n\n') + '_' + t + edits_text
                else:
                    t = title + '\n' + t + edits_text
                await update.message.reply_text(t, parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
                await extra_send_near(update, context)
            elif (not context.user_data.get('EXTRA_CLICKED') and
                  update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']):
                if int(user.number) >= 10:
                    lessons, day = await get_standard_timetable_for_user(f'{user.surname} {user.name}', user.grade,
                                                                         days_from_short_text_to_num[
                                                                             update.message.text])
                else:
                    lessons, day = await get_standard_timetable_for_user_6_9(user.grade,
                                                                             days_from_short_text_to_num[
                                                                                 update.message.text])
                if lessons.empty:
                    txt = (user.surname + ' ' + user.name + ' ' + user.grade)
                    class_txt = user.grade

                    await update.message.reply_text(f'Ученика "{txt}" не найдено или отсутствует '
                                                    f'расписание для {class_txt} класса.')
                    return ConversationHandler.END
                title = f'*Расписание на _{days_from_num_to_full_text_formatted[day]}_*\n\n'
                t = ""
                edits_text = ""
                context.user_data['NEXT_DAY_TT'] = False
                if days_from_short_text_to_num[update.message.text] == 0 and datetime.now().weekday() == 5:
                    context.user_data['NEXT_DAY_TT'] = True
                    edits_text = await get_edits_for_student(context, user.grade)
                elif days_from_short_text_to_num[update.message.text] == datetime.now().weekday():
                    context.user_data['NEXT_DAY_TT'] = False
                    edits_text = await get_edits_for_student(context, user.grade)
                elif days_from_short_text_to_num[update.message.text] == (datetime.now().weekday() + 1) % 7:
                    context.user_data['NEXT_DAY_TT'] = True
                    edits_text = await get_edits_for_student(context, user.grade)
                for txt_info, key in lessons_keys.items():
                    try:
                        if int(user.number) >= 10:
                            pre_lesson_info = lessons.loc[key].split('###')
                        else:
                            pre_lesson_info = lessons.loc[key][day].split('###')

                        t += prepare_for_markdown(txt_info)
                        last_cab = ""
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
                                one_more_teacher_VTEK = (
                                    lesson_name.replace('В', '').replace('Т', '').
                                    replace('Э.', '.').replace('К.', '.').replace('Т.', '.'))
                                cnt = sum([int(i in 'АБВГДЕËЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ') for i in one_more_teacher_VTEK])
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
                        t += '\n'
                    except Exception as e:
                        continue
                if edits_text:
                    t = title + '_' + prepare_for_markdown(
                        '⚠️Обратите внимание, что для Вашего класса ниже есть изменения в расписании!\n\n') + '_' + t + edits_text
                else:
                    t = title + '\n' + t + edits_text
                await update.message.reply_text(t, parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
                await extra_send_day(update)
            elif context.user_data.get('EXTRA_CLICKED') and update.message.text in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']:
                context.user_data['EXTRA_CLICKED'] = False
                await extra_lessons_for_each_day(update, update.message.from_user.id, update.message.text)
            elif update.message.text == '♟️Сегодня♟️':
                today = datetime.now().weekday()
                context.user_data['EXTRA_CLICKED'] = False
                if today == 6:
                    await update.message.reply_text(f'*В воскресенье нужно отдыхать\! Кружков нет\.*',
                                                    reply_markup=await timetable_kbrd(), parse_mode='MarkdownV2')
                    return
                days = {value: key for key, value in days_from_short_text_to_num.items()}
                await extra_lessons_for_each_day(update, update.message.from_user.id, days[today])
            elif update.message.text == '🎭Все кружки🎭':
                context.user_data['EXTRA_CLICKED'] = False
                await extra_lessons_for_all_days(update, update.message.from_user.id)
