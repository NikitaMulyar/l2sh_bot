from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from py_scripts.funcs_back import timetable_kbrd, check_busy, prepare_for_markdown
from sqlalchemy_scripts.extra_lessons import Extra
from sqlalchemy_scripts.user_to_extra import Extra_to_User
from sqlalchemy_scripts.users import User
import pandas as pd
from py_scripts.consts import days_from_num_to_full_text, COMMANDS, BACKREF_CMDS
from sqlalchemy_scripts import db_session


class Extra_Lessons:
    def __init__(self):
        self.cnt = None
        self.lessons = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        user__id = update.message.from_user.id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.telegram_id == user__id).first()
        if not user:
            await update.message.reply_text('⚠️ *Для начала заполните свои данные\: \/start*',
                                            parse_mode='MarkdownV2')
            db_sess.close()
            return ConversationHandler.END
        if user.role == 'admin' or user.role == 'teacher':
            await update.message.reply_text('⚠️ *Вы не можете записываться на кружки*',
                                            parse_mode='MarkdownV2')
            db_sess.close()
            return ConversationHandler.END
        if not list(db_sess.query(Extra).filter(Extra.grade == user.number).all()):
            await update.message.reply_text('⚠️ *Для вашего класса отсутствуют возможные для записи кружки*',
                                            parse_mode='MarkdownV2')
            db_sess.close()
            return ConversationHandler.END
        await update.message.reply_text('🌟 Здесь Вы можете добавить кружки, которые хотели бы увидеть в '
                                        'своем расписании.\n'
                                        'Если захотите закончить, напишите: "/end_extra".\n'
                                        'Давайте начнем выбирать: ✨')
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['extra']])
        context.user_data['choose_count'] = 0
        self.cnt = len(list(db_sess.query(Extra).filter(Extra.grade == user.number).all()))
        self.lessons = list(db_sess.query(Extra).filter(Extra.grade == user.number).all())
        db_sess.close()
        return await self.choose_extra(update, context)

    async def choose_extra(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data['choose_count'] == self.cnt:
            await update.callback_query.edit_message_text(
                '🌟 Загрузка кружков завершена! Теперь Вы можете посмотреть своё расписание с кружками.',
                reply_markup="")
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        lesson = self.lessons[context.user_data['choose_count']]
        context.user_data['choose_count'] += 1
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

    async def timeout_func(self, update: Update, context: CallbackContext):
        cmd = BACKREF_CMDS[context.user_data["DIALOG_CMD"]]
        await context.bot.send_message(update.effective_chat.id, '⚠️ *Время ожидания вышло\. '
                                                                 'Чтобы начать заново\, введите команду\: '
                                                                 f'{prepare_for_markdown(cmd)}*',
                                       parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        context.user_data["DIALOG_CMD"] = None
        context.user_data['in_conversation'] = False

    async def get_out(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            '🌟 Загрузка кружков завершена! Теперь Вы можете посмотреть своё расписание с кружками.',
            reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
