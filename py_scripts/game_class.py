import os.path
import random
import aiohttp
from telegram import Update
import telegram
from telegram.ext import ContextTypes
from random import shuffle
from py_scripts.funcs_back import check_busy
from py_scripts.config import game_api
import pandas as pd
import numpy as np


class GameMillioner:
    client = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
    url = 'https://engine.lifeis.porn/api/millionaire.php'
    path = 'data/game.csv'

    async def send_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Called by the command /game"""
        is_busy = await check_busy(update, context)
        if is_busy:
            return

        level = random.randint(1, 3)
        res = await self.client.get(self.url, params={
            'qType': level, 'count': 1, 'apikey': game_api
        })
        res = await res.json(content_type=None)
        ans = res['data'][0]['answers']
        correct = ans[0]
        shuffle(ans)
        correct_id = ans.index(correct)

        poll = await context.bot.send_poll(update.message.chat.id, res['data'][0]['question'],
                                           options=ans, type=telegram.Poll.QUIZ,
                                           correct_option_id=correct_id, open_period=20,
                                           is_anonymous=False)
        context.bot_data[str(poll.poll.id)] = [poll.poll.correct_option_id, level + 1]

    async def get_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chosen_id = update.poll_answer.option_ids[0]
        user = update.poll_answer.user
        if chosen_id == context.bot_data[str(update.poll_answer.poll_id)][0]:
            cnt = context.bot_data[str(update.poll_answer.poll_id)][1] ** 3
            await user.send_message(f'Верно! +{cnt} очков')
        else:
            cnt = context.bot_data[str(update.poll_answer.poll_id)][1] ** 2
            await user.send_message(f'Неверно. -{cnt} очков')
            cnt = -cnt

        if not os.path.exists(self.path):
            with open(self.path, mode='w', encoding='utf-8') as f:
                df = pd.DataFrame(columns=['points'])
                df.loc[user.id] = [cnt]
                df.to_csv(self.path)
                f.write('')
            f.close()
        else:
            df = pd.read_csv(self.path)
            df.set_index('Unnamed: 0', inplace=True)
            if user.id not in df.index.values.tolist():
                df.loc[user.id] = [cnt]
            else:
                df.loc[user.id]['points'] += cnt
            df.to_csv(self.path)

        await user.send_message(f'Счёт: {df.loc[user.id]["points"]} очков')
        await user.send_message('Новый вопрос: /game')

