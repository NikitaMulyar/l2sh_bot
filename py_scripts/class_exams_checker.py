from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ConversationHandler, ContextTypes, CallbackContext
from py_scripts.consts import COMMANDS, BACKREF_CMDS
from py_scripts.funcs_back import prepare_for_markdown, timetable_kbrd, check_busy, throttle, throttle2
from py_scripts.security import check_hash
from sqlalchemy_scripts.users import User
from sqlalchemy_scripts import db_session
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date


async def save_exams_in_csv():
    soup = BeautifulSoup(open('bot_files/exams.html').read(), 'html.parser')
    result = []
    txt_to_int = {'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'мая': 5,
                  'июн': 6, 'авг': 8, 'сент': 9, 'окт': 10, 'ноя': 11, 'дек': 12}

    fl = True
    header = []
    for link in soup.find_all('tr'):
        r = link.find_all('td')
        txts_cols = []
        i = 0
        for el in r:
            txts_cols.append([el.text, int(el.get('colspan', '1')), int(el.get('rowspan', '1'))])
        if txts_cols and (txts_cols[0][0] or txts_cols[1][0]):
            del txts_cols[2]
            txts_cols[0], txts_cols[1] = txts_cols[1], txts_cols[0]
            if txts_cols[0][0][0].isalpha():
                if fl:
                    fl = False
                    header = txts_cols.copy()
                continue
            tmp = [txt_to_int[i] for i in txt_to_int.keys() if i in txts_cols[0][0]]
            if tmp:
                tmp = tmp[0]
                year = date.today().year
                month = date.today().month
                if 7 <= tmp <= 11 and 0 <= month <= 5:
                    year -= 1
                elif 7 <= month <= 11 and 0 <= tmp <= 5:
                    year += 1
                txts_cols[0][0] = date(year, tmp, int(txts_cols[0][0].split()[0]))
            result.append(txts_cols)
    len_ = len(result) + 1
    matrix = [[] for _ in range(len_)]
    for el in header:
        if el[0]:
            for i in range(el[1]):
                matrix[0].append(el[0])
    row_len = len(matrix[0])
    for i in range(1, len_):
        matrix[i] = ['' for _ in range(row_len)]

    for i in range(len_ - 1):
        ind = 0
        for j in range(len(result[i])):
            for k in range(result[i][j][1]):
                matrix[i + 1][ind] = result[i][j][0]
                if isinstance(matrix[i + 1][ind], str):
                    matrix[i + 1][ind] = matrix[i + 1][ind].strip()
                ind += 1
                if ind == row_len:
                    break
            if ind == row_len:
                break
    df = pd.DataFrame(matrix[1:], columns=matrix[0])
    df.to_csv('bot_files/exams.csv', index=False)


class LoadHTMLExams:
    step_pswrd = 1
    step_file = 2

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['exams_load']])
        context.user_data['in_conversation'] = True
        chat_id = update.message.chat_id
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.chat_id == chat_id).first()
        await update.message.reply_text('Прервать загрузку графика КР: /end_exams_load')
        if user and user.role == "admin":
            db_sess.close()
            await update.message.reply_text('Загрузите файл формата .html')
            return self.step_file
        db_sess.close()
        await update.message.reply_text('Введите пароль админа:')
        return self.step_pswrd

    async def get_pswrd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_hash(update.message.text):
            await update.message.reply_text('⚠️ *Неверный пароль\. Загрузка графика прервана\. '
                                            'Начать сначала\: \/exams_load*', parse_mode='MarkdownV2')
            context.user_data['in_conversation'] = False
            context.user_data['DIALOG_CMD'] = None
            return ConversationHandler.END
        await update.message.reply_text('Загрузите файл формата .html')
        return self.step_file

    async def load_html(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        file_info = await context.bot.get_file(update.message.document.file_id)
        await file_info.download_to_drive(f"bot_files/exams.html")
        msg_ = await update.message.reply_text('⏳ *Идет формирование файла с графиком КР в боте\. '
                                               'Время ожидания \- до 1 минуты*', parse_mode='MarkdownV2')
        try:
            await save_exams_in_csv()
            await context.bot.delete_message(update.message.chat_id, msg_.id)
        except Exception as e:
            await context.bot.delete_message(update.message.chat_id, msg_.id)
            await update.message.reply_text(f'⚠️ *При попытке сформировать график произошла '
                                            f'ошибка\: {prepare_for_markdown(e.__str__())}\. Проверьте формат файла и '
                                            f'попробуйте загрузить файл еще раз*',
                                            parse_mode='MarkdownV2')
            return self.step_file
        await update.message.reply_text(f'Файл успешно загружен. Начать сначала: /exams_load')
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END

    async def timeout_func(self, update: Update, context: CallbackContext):
        cmd = BACKREF_CMDS[context.user_data["DIALOG_CMD"]]
        await context.bot.send_message(update.effective_chat.id, '⚠️ *Время ожидания вышло\. '
                                                                 'Чтобы начать заново\, введите команду\: '
                                                                 f'{prepare_for_markdown(cmd)}*',
                                       parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None

    async def end_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('⚠️ *Загрузка графика прервана\. Начать сначала\: \/exams\_load*',
            parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END


class CheckClassExam:
    step_month = 1
    step_class = 2
    months = {'Авг': 8, 'Сент': 9, 'Окт': 10, 'Ноя': 11, 'Дек': 12, 'Янв': 1, 'Фев': 2, 'Мар': 3, 'Апр': 4,
              'Май': 5, 'Июн': 6}
    reverse_months = {1: 'январь', 2: 'февраль', 3: 'март', 4: 'апрель', 5: 'май', 6: 'июнь',
                      8: 'август', 9: 'сентябрь', 10: 'октябрь', 11: 'ноябрь', 12: 'декабрь'}

    async def classes_buttons(self):
        classes = [['6А', '6Б', '6В'], *[[f'{i}{j}' for j in 'АБВГД'] for i in range(7, 12)],
                   ['Выбор периода']]
        kbd = ReplyKeyboardMarkup(classes, resize_keyboard=True)
        return kbd

    async def months_buttons(self):
        months_ = [list(self.months.keys())[i: i + 3] for i in range(0, len(self.months.keys()), 3)]
        kbd = ReplyKeyboardMarkup(months_, resize_keyboard=True)
        return kbd

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = "".join(['/', COMMANDS['exams']])
        await update.message.reply_text('Чтобы выйти, напишите: /end_exams.\nВыберите период', reply_markup=await
        self.months_buttons())
        return self.step_month

    async def get_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.months.get(update.message.text):
            await update.message.reply_text('Выберите период')
            return self.step_month
        context.user_data['exam_month'] = self.months[update.message.text]
        await update.message.reply_text('Выберите класс', reply_markup=await self.classes_buttons())
        return self.step_class

    @throttle2()
    async def get_class(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == 'Выбор периода':
            await update.message.reply_text('Выберите период', reply_markup=await self.months_buttons())
            return self.step_month
        context.user_data['exam_class'] = update.message.text
        df = pd.read_csv('bot_files/exams.csv')
        if context.user_data['exam_class'] not in df.columns.values:
            if context.user_data['exam_class'][:-1] + ' ' + context.user_data['exam_class'][-1] not in df.columns.values:
                await update.message.reply_text('Данный класс отсутствует в записях. Выберите класс')
                return self.step_class
            context.user_data['exam_class'] = context.user_data['exam_class'][:-1] + ' ' + context.user_data[
                'exam_class'][-1]
        cl = context.user_data['exam_class']
        df.fillna('', inplace=True)
        df[cl] = df[cl] + '###' + df[f'{cl}.1']
        df = df[['Дата', cl]]
        df['Дата'] = pd.to_datetime(df['Дата'])
        df = df[df['Дата'].dt.month == context.user_data['exam_month']]
        t = (f"*📆 График контрольных работ на {self.reverse_months[context.user_data['exam_month']]} для {cl} "
             f"класса*\n\n")
        fl = False
        for i in range(len(df.index.values)):
            t_ = df.iloc[i]
            r = t_[cl].split('###')
            while '' in r:
                r.remove('')
            if not r:
                continue
            fl = True
            t += prepare_for_markdown(f"{t_['Дата'].date().strftime('%d.%m.%Y')} - {r[0]}\n")
        if not fl:
            t += 'Контрольных в данном периоде нет\.'
        await update.message.reply_text(t, parse_mode='MarkdownV2')
        await update.message.reply_text('Выберите класс')
        return self.step_class

    async def timeout_func(self, update: Update, context: CallbackContext):
        cmd = BACKREF_CMDS[context.user_data["DIALOG_CMD"]]
        await context.bot.send_message(update.effective_chat.id, '⚠️ *Время ожидания вышло\. '
                                                                 'Чтобы начать заново\, введите команду\: '
                                                                 f'{prepare_for_markdown(cmd)}*',
                                       parse_mode='MarkdownV2', reply_markup=await timetable_kbrd())
        context.user_data["DIALOG_CMD"] = None
        context.user_data['exam_class'] = None
        context.user_data['exam_month'] = None
        context.user_data['in_conversation'] = False

    async def end_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Просмотр контрольных завершен. Начать сначала: /exams',
                                        reply_markup=await timetable_kbrd())
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        context.user_data['exam_class'] = None
        context.user_data['exam_month'] = None
        return ConversationHandler.END
