import aiohttp
import wolframalpha
from telegram import Update, InputMediaDocument
from telegram.ext import ContextTypes, ConversationHandler, CallbackContext
from py_scripts.funcs_back import check_busy, prepare_for_markdown, throttle
from py_scripts.consts import COMMANDS, BACKREF_CMDS
from py_scripts.config import app_id


class WolframClient:
    step_request = 1

    async def get_response(self, req):
        client = wolframalpha.Client(app_id)
        session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
        res = await client.query(req)
        if not res.get('pod'):
            await session.close()
            return []
        imgs = []
        if isinstance(res['pod'], list):
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
        else:
            el = res['pod']['subpod']
            if isinstance(el, list):
                for el2 in el:
                    el2 = await session.get(el2['img']['@src'])
                    el2 = await el2.content.read()
                    imgs.append(el2)
            else:
                el = await session.get(el['img']['@src'])
                el = await el.content.read()
                imgs.append(el)
        if not imgs:
            await session.close()
            return []
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

    async def send_response_(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        msg = await update.message.reply_text(f'⏳ *Запрос принят\. Время ожидания \- 5\-10 секунд*',
                                              parse_mode='MarkdownV2')
        res = await self.get_response(text)
        await context.bot.delete_message(update.message.chat.id, msg.id)
        if not res:
            await update.message.reply_text(f'Некорректный запрос. Попробуйте снова.\n'
                                            f'Завершить wolfram: /end_wolfram')
            return self.step_request
        for group in res:
            await context.bot.send_media_group(update.message.chat.id, group)
        await update.message.reply_text('А вот и ответ! Жду новый запрос! (Без префикса /wolfram)')
        await update.message.reply_text(f'Завершить wolfram: /end_wolfram')
        return self.step_request

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_busy = await check_busy(update, context)
        if is_busy:
            return ConversationHandler.END
        context.user_data['in_conversation'] = True
        context.user_data['DIALOG_CMD'] = '/' + COMMANDS['wolfram']
        if context.args:
            return await self.send_response_(update, context,
                                             " ".join([str(el) for el in context.args]))
        await update.message.reply_text(f'Привет!\n'
                                        f'С помощью этой команды можно сделать запрос на сайт https://www.wolframalpha.com/ !\n'
                                        f'Ответ придет в виде картинок.\n'
                                        f'Введите запрос:')
        return self.step_request

    @throttle(seconds=5)
    async def send_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self.send_response_(update, context, update.message.text)

    async def timeout_func(self, update: Update, context: CallbackContext):
        cmd = BACKREF_CMDS[context.user_data["DIALOG_CMD"]]
        await context.bot.send_message(update.effective_chat.id, '⚠️ *Время ожидания вышло\. '
                                                                 'Чтобы начать заново\, введите команду\: '
                                                                 f'{prepare_for_markdown(cmd)}*',
                                       parse_mode='MarkdownV2')
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None

    async def end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Завершено. Начать заново: /wolfram')
        context.user_data['in_conversation'] = False
        context.user_data['DIALOG_CMD'] = None
        return ConversationHandler.END
