from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, ContextTypes
from py_scripts.funcs_back import timetable_kbrd, check_busy
from sqlalchemy_scripts.extra_lessons import Extra
from sqlalchemy_scripts.user_to_extra import Extra_to_User
from sqlalchemy_scripts.users import User
import pandas as pd
from py_scripts.consts import days_from_num_to_full_text, COMMANDS
from sqlalchemy_scripts import db_session


class Extra_Lessons:
    def __init__(self):
        self.count = {}
        db_sess = db_session.create_session()
        for i in range(6):
            counter = 0
            extra_lessons = pd.read_excel('data/extra.xlsx', sheet_name=i, usecols=[2, 4, 6, 8, 10, 12]).values
            length = len(extra_lessons)
            for j in range(6):
                k = 1
                while k <= length:
                    if not pd.isnull(extra_lessons[k][j]):
                        title = extra_lessons[k][j]
                        place = extra_lessons[k + 4][j]
                        for l in range(1, 4):
                            if not pd.isnull(extra_lessons[k + l][j]):
                                if ("-" in extra_lessons[k + l][j] and (
                                        "." in extra_lessons[k + l][j] or ":" in extra_lessons[k + l][j])) or (
                                        "переменах" in extra_lessons[k + l][j]):
                                    time = extra_lessons[k + l][j]
                                elif "Код" not in extra_lessons[k + l][j] and all(
                                        el.isalpha() for el in
                                        "".join(extra_lessons[k + l][j].replace(".", "").replace(",", "").split())):
                                    teacher = extra_lessons[k + l][j]
                                    break
                        day = days_from_num_to_full_text[j]
                        teacher = teacher.replace('ё', 'е')
                        extra = Extra(title=title, time=time, day=day, teacher=teacher, place=place, grade=i + 6)
                        if not bool(db_sess.query(Extra).filter(Extra.title == title, Extra.grade == i + 6,
                                                                Extra.day == day).first()):
                            db_sess.add(extra)
                        else:
                            extra = db_sess.query(Extra).filter(Extra.title == title, Extra.grade == i + 6,
                                                                Extra.day == day).first()
                            extra.teacher = teacher
                            extra.time = time
                        counter += 1
                    k += 6
            self.count[i + 6] = counter
        db_sess.commit()
        db_sess.close()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        user__id = update.message.from_user.id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        db_sess.close()
        if not user:
            await update.message.reply_text('⚠️ *Для начала заполните свои данные\: \/start*',
                                            parse_mode='MarkdownV2')
            return ConversationHandler.END
        if user.role == 'admin' or user.role == 'teacher':
            await update.message.reply_text('⚠️ *Вы не можете записываться на кружки*',
                                            parse_mode='MarkdownV2')
            return ConversationHandler.END
        await update.message.reply_text('🌟 Здесь Вы можете добавить кружки, которые хотели бы увидеть в '
                                        'своем расписании.\n'
                                        'Если захотите закончить, напишите: "/end_extra".\n'
                                        'Давайте начнем выбирать: ✨')
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['extra']])
        context.user_data['choose_count'] = 0
        return await self.choose_extra(update, context)

    async def choose_extra(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            user__id = update.message.from_user.id
        else:
            user__id = update.callback_query.from_user.id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        grade = user.number

        if context.user_data['choose_count'] == self.count[int(grade)]:
            db_sess.close()
            await update.callback_query.edit_message_text('🌟 Загрузка кружков завершена! Большое спасибо за Ваш '
                                                          'выбор! 🙌🏻 Теперь Вы можете посмотреть своё расписание с кружками.',
                                                          reply_markup="")
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        lesson = list(db_sess.query(Extra).filter(Extra.grade == grade).all())[context.user_data['choose_count']]
        context.user_data['choose_count'] += 1
        while lesson.teacher.count(".") <= 1 and user.grade not in lesson.teacher:
            lesson = list(db_sess.query(Extra).filter(Extra.grade == grade).all())[context.user_data['choose_count']]
            context.user_data['choose_count'] += 1
        db_sess.close()
        context.user_data['lesson'] = lesson
        if "зал" in lesson.place or "онлайн" in lesson.place:
            place = lesson.place
        else:
            place = f"{lesson.place} кабинет"
        text = f"""📅 {lesson.day} 📅\n {lesson.title} - {lesson.teacher} \n⏰ {lesson.time} ⏰\n🏫 {place} 🏫\nБудешь посещать?"""
        keyboard = [[InlineKeyboardButton("Да", callback_data="1"),
                     InlineKeyboardButton("Нет", callback_data="2")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        return 1

    async def yes_no(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        num = query.data
        user__id = query.from_user.id
        db_sess = db_session.create_session()
        extra = db_sess.query(Extra_to_User).filter(Extra_to_User.user_id == user__id,
                                                    Extra_to_User.extra_id == context.user_data[
                                                        'lesson'].id).first()
        if num == '1':
            if not bool(extra):
                extra_to_user = Extra_to_User(user_id=user__id, extra_id=context.user_data['lesson'].id)
                db_sess.add(extra_to_user)
        else:
            if bool(extra):
                db_sess.delete(extra)
        db_sess.commit()
        db_sess.close()
        return await self.choose_extra(update, context)

    async def get_out(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('🌟 Загрузка кружков завершена! Большое спасибо за Ваш '
                                        'выбор! 🙌🏻 Теперь Вы можете посмотреть своё расписание с кружками.',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
