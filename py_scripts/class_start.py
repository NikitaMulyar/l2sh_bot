import random
import string

from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from telegram import ReplyKeyboardMarkup, Update
from py_scripts.security import check_hash
from sqlalchemy_scripts.users import User
from py_scripts.funcs_back import timetable_kbrd, put_to_db, check_busy, prepare_for_markdown
from py_scripts.consts import COMMANDS, BACKREF_CMDS
from sqlalchemy_scripts import db_session


class SetTimetable:
    step_class = 1
    step_familia = 2
    step_name = 3
    step_pswrd = 4
    step_third_name = 5
    classes = ['6А', '6Б', '6В'] + [f'{i}{j}' for i in range(7, 12) for j in 'АБВГД'] + ['Админ', 'Учитель']
    command = '/start'

    async def classes_buttons(self):
        classes = [['Админ', 'Учитель']] + [['6А', '6Б', '6В']] + [[f'{i}{j}' for j in 'АБВГД'] for i in range(7, 12)]
        kbd = ReplyKeyboardMarkup(classes, resize_keyboard=True, one_time_keyboard=True)
        return kbd

    async def create_uid(self):
        s = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        uid = "".join([random.choice(s) for i in range(4)])
        db_sess = db_session.create_session()
        res = db_sess.query(User).filter(User.uid == uid).first()
        while res:
            uid = "".join([random.choice(s) for i in range(4)])
            res = db_sess.query(User).filter(User.uid == uid).first()
        db_sess.close()
        return uid

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = '/' + COMMANDS['start']
        chat_id = update.message.chat_id
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.chat_id == chat_id).first():
            db_sess.close()
            await update.message.reply_text(
                'Здравствуйте! Я вижу, что Вы уже есть в системе.\n'
                'Можете пользоваться ботом.\n'
                'Все команды бота доступны в кнопке "Меню".\n⚠️ Обращаем внимание, что с 10 марта 2024 '
                'года вступает в силу Пользовательское Соглашение. Подробнее: '
                'https://telegra.ph/Polzovatelskoe-soglashenie-po-ispolzovaniyu-Telegram-bota-Raspisanie-L2SH-03-08',
                reply_markup=await timetable_kbrd())
            context.user_data['DIALOG_CMD'] = None
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        db_sess.close()
        await update.message.reply_text(
            'Здравствуйте! В этом боте Вы можете узнавать расписание на день!\n'
            'Сначала выберите свою должность/класс.\n'
            'Для остановки регистрации напишите: /end\n'
            '⚠️ Продолжая регистрацию, вы соглашаетесь с Пользовательским Соглашением: '
            'https://telegra.ph/Polzovatelskoe-soglashenie-po-ispolzovaniyu-Telegram-bota-Raspisanie-L2SH-03-08',
            reply_markup=await self.classes_buttons())
        context.user_data['INFO'] = dict()
        return self.step_class

    async def get_class(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text not in self.classes:
            await update.message.reply_text(f'⚠️ *Указан неверный класс \"{prepare_for_markdown(update.message.text)}\"*',
                                            reply_markup=await self.classes_buttons(),
                                            parse_mode='MarkdownV2')
            return self.step_class
        chat_id = update.message.chat_id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        if user and update.message.text == 'Админ' and user.role != "admin":
            db_sess.close()
            context.user_data['INFO']['Class'] = "admin"
            await update.message.reply_text('Введите пароль:')
            return self.step_pswrd
        elif update.message.text == 'Админ':
            db_sess.close()
            context.user_data['INFO']['Class'] = "admin"
            await update.message.reply_text('Введите пароль:')
            return self.step_pswrd
        if update.message.text == 'Учитель':
            context.user_data['INFO']['Class'] = "teacher"
        elif update.message.text == 'Админ':
            context.user_data['INFO']['Class'] = "admin"
        else:
            context.user_data['INFO']['Class'] = update.message.text
        await update.message.reply_text('Укажите свою фамилию (пример: Некрасов)')
        db_sess.close()
        return self.step_familia

    async def get_psw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_hash(update.message.text):
            await update.message.reply_text(f'⚠️ *Неверный пароль\. Настройка данных прервана\. '
                                            f'Начать сначала\: {prepare_for_markdown(self.command)}*',
                                            reply_markup=await timetable_kbrd(),
                                            parse_mode='MarkdownV2')
            context.user_data['in_conversation'] = False
            context.user_data['INFO'] = dict()
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await update.message.reply_text('Укажите свою фамилию (пример: Некрасов)')
        return self.step_familia

    async def get_familia(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['INFO']['Familia'] = update.message.text.replace("ё", "е")
        await update.message.reply_text('Укажите свое ПОЛНОЕ имя (пример: Николай)')
        return self.step_name

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['INFO']['Name'] = update.message.text.replace("ё", "е")
        if context.user_data['INFO']['Class'] == 'admin' or context.user_data['INFO']['Class'] == 'teacher':
            await update.message.reply_text('Напишите, пожалуйста, свое отчество')
            return self.step_third_name
        uid = await self.create_uid()
        put_to_db(update, context.user_data['INFO']['Name'], context.user_data['INFO']['Familia'],
                  'student', update.message.from_user.username, grade=context.user_data['INFO']['Class'],
                  uid=uid)
        await update.message.reply_text(f'Спасибо! Теперь Вы можете пользоваться ботом.\n'
                                        f'Ваш UID (доступен в Профиле по команде /profile): {uid}',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        context.user_data['INFO'] = dict()
        return ConversationHandler.END

    async def get_third_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['INFO']['Otchestvo'] = update.message.text.replace("ё", "е")
        uid = await self.create_uid()
        put_to_db(update, context.user_data['INFO']['Name'] + ' ' +
                  context.user_data['INFO']['Otchestvo'], context.user_data['INFO']['Familia'],
                  context.user_data['INFO']['Class'], update.message.from_user.username,
                  uid=uid)
        await update.message.reply_text('Спасибо! Теперь Вы можете пользоваться ботом.\n'
                                        f'Ваш UID (доступен в Профиле по команде /profile): {uid}',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        context.user_data['INFO'] = dict()
        return ConversationHandler.END

    async def timeout_func(self, update: Update, context: CallbackContext):
        cmd = BACKREF_CMDS[context.user_data["DIALOG_CMD"]]
        await context.bot.send_message(update.effective_chat.id, '⚠️ *Время ожидания вышло\. '
                                                                 'Чтобы начать заново\, введите команду\: '
                                                                 f'{prepare_for_markdown(cmd)}*',
                                       parse_mode='MarkdownV2')
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        context.user_data['INFO'] = dict()

    async def end_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['in_conversation'] = False
        context.user_data['INFO'] = dict()
        context.user_data['DIALOG_CMD'] = None
        await update.message.reply_text(f'Регистрация в системе прервана. Начать сначала: {self.command}',
                                        reply_markup=await timetable_kbrd())
        return ConversationHandler.END
