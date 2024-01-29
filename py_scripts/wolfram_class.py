import aiohttp
import wolframalpha
from telegram import Update, InputMediaDocument
from telegram.ext import ContextTypes, ConversationHandler
from py_scripts.funcs_back import check_busy
from py_scripts.consts import COMMANDS
from py_scripts.config import app_id


class WolframClient:
    client = wolframalpha.Client(app_id)
    step_request = 1

    async def get_response(self, req):
        session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
        res = await self.client.query(req)
        if not res.get('pod'):
            await session.close()
            return []
        imgs = []
        for el in res['pod']:
            el = el['subpod']
            if isinstance(el, list):
                for el2 in el:
                    el2 = await session.get(el2['img']['@src'])
                    el2 = await el2.content.read()
                    imgs.append(el2)
            else:
                el = await session.get(el['img']['@src'])
                el = await el.content.read()
                imgs.append(el)

        arr = []
        group = []
        i = 0
        for el in imgs:
            group.append(InputMediaDocument(el, filename=f'{i}.png'))
            if len(group) == 10:
                arr.append(group)
                group = []
            i += 1
        if group:
            arr.append(group)
        await session.close()
        return arr

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        await update.message.reply_text(f'Привет!\n'
                                        f'С помощью этой команды можно сделать запрос на сайт https://www.wolframalpha.com/ !\n'
                                        f'Ответ придет в виде картинок.\n'
                                        f'Введите запрос:')
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = COMMANDS['wolfram']
        return self.step_request

    async def send_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text(f'⏳Запрос принят. Время ожидания 5-10 секунд...')
        res = await self.get_response(update.message.text)
        await context.bot.delete_message(update.message.chat.id, msg.id)
        if not res:
            await update.message.reply_text(f'Некорректный запрос. Попробуйте снова.\n'
                                            f'Завершить wolfram: /end_wolfram')
            return self.step_request
        for group in res:
            await context.bot.send_media_group(update.message.chat.id, group)
        await update.message.reply_text('А вот и ответ! Жду новый запрос!')
        await update.message.reply_text(f'Завершить wolfram: /end_wolfram')
        return self.step_request

    async def end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Завершено. Начать заново: /wolfram')
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
