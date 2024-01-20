from telegram import (KeyboardButton, KeyboardButtonPollType, Poll, ReplyKeyboardMarkup,
                      ReplyKeyboardRemove, Update)
import telegram
from telegram.ext import (Application, CommandHandler, ContextTypes, MessageHandler,
                          PollAnswerHandler, PollHandler, filters, ConversationHandler)
import requests
from random import shuffle
from py_scripts.funcs_back import check_busy


class GameMillioner:
    step_poll = 1
    step_answer = 2
    step_next = 3
    step_results = 4

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return
        await update.message.reply_text('Игра в разработке. Дата выхода: весна 2024')
        return ConversationHandler.END
        await update.message.reply_text('Готов?', reply_markup=ReplyKeyboardMarkup([['Да', 'Нет']],
                                                                                   one_time_keyboard=True),)
        return self.step_poll

    async def send_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == 'Нет':
            await update.message.reply_text('Пока!')
            return ConversationHandler.END
        res = requests.get('https://engine.lifeis.porn/api/millionaire.php', params={
            'qType': 1, 'count': 1
        }).json()
        ans = res['data'][0]['answers']
        correct = ans[res['data'][0]['id']]
        shuffle(ans)
        correct_id = ans.index(correct)

        msg = await context.bot.send_poll(update.message.chat.id, res['data'][0]['question'],
                                    options=ans, type=telegram.Poll.QUIZ,
                                    correct_option_id=correct_id,
                                    open_period=30)
        context.user_data['poll_info'] = {'correct_id': correct_id, 'poll': msg.poll}
        return self.step_answer

    async def get_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(111)
        chosen_id = update.poll_answer.option_ids[0]
        if chosen_id != context.user_data['poll_info']['correct_id']:
            await update.message.reply_text('Неверно.')
        else:
            await update.message.reply_text('Верно.')
        await update.message.reply_text('Готов?', reply_markup=ReplyKeyboardMarkup([['Да', 'Нет']],
                                                                                   one_time_keyboard=True))
        return self.step_poll

    async def end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Пока...')
        return ConversationHandler.END


