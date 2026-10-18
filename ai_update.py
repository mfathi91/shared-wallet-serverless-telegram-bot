import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    filters,
    MessageHandler
)

from configuration import Configuration
from payment import Payment

# State of the AI conversation (must differ from the states used in main.py)
AI_TEXT = 10

DEFAULT_GEMINI_MODEL = 'gemini-3.5-flash-lite'
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
GEMINI_TIMEOUT_SECONDS = 15

AMOUNT_REGEX = r'[0-9]+(.[0-9]{2})?'
REQUIRED_FIELDS = ['wallet', 'payer', 'amount']
FIELD_NAMES = ['wallet', 'payer', 'amount', 'note']

RESPONSE_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'wallet': {'type': 'STRING', 'nullable': True},
        'payer': {'type': 'STRING', 'nullable': True},
        'amount': {'type': 'STRING', 'nullable': True},
        'note': {'type': 'STRING', 'nullable': True},
    },
    'required': FIELD_NAMES,
}

AI_ERROR_TEXT = ('AI service error, please try again or use /update.\n'
                 'خطا در سرویس هوش مصنوعی، لطفاً دوباره تلاش کنید یا از /update استفاده کنید.')
NOT_CONFIGURED_TEXT = ('AI update is not configured. Please use /update.\n'
                       'به‌روزرسانی با هوش مصنوعی تنظیم نشده است. لطفاً از /update استفاده کنید.')


def _build_prompt(text: str, sender_name: Optional[str], config: Configuration) -> str:
    wallets = ', '.join(config.get_currencies())
    users = ', '.join(config.get_usernames())
    sender = sender_name if sender_name else 'unknown'
    return (
        'You extract a shared-wallet payment from a short message written mostly in Persian '
        '(sometimes in English). Return only the JSON object described by the schema.\n\n'
        f'Allowed wallets (wallet field): {wallets}\n'
        f'Allowed users (payer field): {users}\n'
        f'The sender of the message is: {sender}\n\n'
        'Rules:\n'
        '- amount: plain ASCII digits only, with no separators. Convert Persian (۰-۹) and Arabic digits to ASCII. '
        'Convert multipliers to a plain number: «هزار» = 1000, «میلیون» = 1000000, "k" = 1000 '
        '(for example «۲۵۰ هزار» -> "250000"). Do not include currency words in amount.\n'
        '- wallet: map «تومن» or «تومان» to "Toman", «دلار» to "Dollar", «یورو» to "Euro". '
        'The result must be one of the allowed wallets, otherwise null.\n'
        '- payer: the person who PAID, i.e. whose balance increases. The words «من», "I" and "me" mean the sender. '
        'Must be one of the allowed users, otherwise null.\n'
        '- note: a short description of what the payment was for, in the original language of the message. '
        'null if there is no description.\n'
        '- Never guess. If a value is not stated or is unclear, return null.\n\n'
        f'Message: {text}'
    )


async def extract_payment(text: str, sender_name: Optional[str], config: Configuration) -> Dict[str, Any]:
    """Ask Gemini to extract wallet, payer, amount and note from a free-text message.

    Raises an exception on HTTP errors, timeouts or unparseable responses.
    """
    api_key = os.environ.get('GEMINI_API_KEY', '')
    model = os.environ.get('GEMINI_MODEL') or DEFAULT_GEMINI_MODEL
    body = {
        'contents': [{'parts': [{'text': _build_prompt(text, sender_name, config)}]}],
        'generationConfig': {
            'responseMimeType': 'application/json',
            'responseSchema': RESPONSE_SCHEMA,
            'temperature': 0,
        },
    }
    async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT_SECONDS) as client:
        response = await client.post(
            GEMINI_URL.format(model=model),
            headers={'x-goog-api-key': api_key, 'Content-Type': 'application/json'},
            json=body,
        )
        response.raise_for_status()
        data = response.json()

    raw_text = data['candidates'][0]['content']['parts'][0]['text']
    fields = json.loads(raw_text)
    if not isinstance(fields, dict):
        raise ValueError('Gemini response is not a JSON object')
    return {name: fields.get(name) for name in FIELD_NAMES}


def _clean_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip()


def validate(fields: Dict[str, Any], config: Configuration) -> Tuple[Dict[str, str], List[str]]:
    """Validate the fields returned by the AI. Returns (clean_fields, missing_required_fields)."""
    wallet = _clean_value(fields.get('wallet'))
    payer = _clean_value(fields.get('payer'))
    amount = _clean_value(fields.get('amount'))
    note = _clean_value(fields.get('note'))

    missing: List[str] = []
    if not wallet or wallet not in config.get_currencies():
        missing.append('wallet')
    if not payer or payer not in config.get_usernames():
        missing.append('payer')
    if not amount or not re.fullmatch(AMOUNT_REGEX, amount):
        missing.append('amount')

    clean = {
        'wallet': wallet or '',
        'payer': payer or '',
        'amount': amount or '',
        'note': note if note else '-',
    }
    return clean, missing


def _sender_name(config: Configuration, chat_id: int) -> Optional[str]:
    for name in config.get_usernames():
        if config.get_chat_id(name) == chat_id:
            return name
    return None


def build_smart_update_handler(config: Configuration, update_end, cancel, confirm_state) -> ConversationHandler:
    """Build the /smartupdate conversation. `update_end` and `cancel` are reused from main.py."""

    async def smart_update_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        logging.info('User %s issued /smartupdate command', update.message.from_user.first_name)
        if not os.environ.get('GEMINI_API_KEY'):
            await update.message.reply_text(NOT_CONFIGURED_TEXT)
            return ConversationHandler.END
        await update.message.reply_text(
            'Describe the payment in one message: wallet, who paid, amount and an optional note. '
            'Example: «۲۵۰ هزار تومن من برای شام دادم». Send /cancel to exit.\n'
            'پرداخت را در یک پیام توضیح دهید: کیف پول، پرداخت‌کننده، مبلغ و توضیح اختیاری. '
            'مثال: «۲۵۰ هزار تومن من برای شام دادم». برای خروج /cancel را بفرستید.',
            reply_markup=ReplyKeyboardRemove(),
        )
        return AI_TEXT

    async def smart_update_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text
        sender = _sender_name(config, update.message.chat_id)
        try:
            fields = await extract_payment(text, sender, config)
        except Exception as ex:
            # Do not log the request (it contains the API key header) - only the error type
            logging.error('AI payment extraction failed: %s', type(ex).__name__)
            await update.message.reply_text(AI_ERROR_TEXT)
            return AI_TEXT

        clean, missing = validate(fields, config)
        if missing:
            missing_str = ', '.join(missing)
            await update.message.reply_text(
                f'Data is not complete (missing: {missing_str}). Please enter again.\n'
                f'اطلاعات کامل نیست ({missing_str}). لطفاً دوباره وارد کنید.'
            )
            return AI_TEXT

        logging.info('User %s extracted /smartupdate parameters: %s', update.message.from_user.first_name, clean)
        payment = Payment(clean['payer'], clean['amount'], clean['wallet'],
                          config.get_wallet_symbol(clean['wallet']), clean['note'])
        context.chat_data['payment'] = payment
        reply_keyboard = [['Yes', 'No']]
        await update.message.reply_text(
            text=f'Do you confirm the following payment?\n{payment.format()}',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                             input_field_placeholder='Yes or No'),
        )
        return confirm_state

    return ConversationHandler(
        entry_points=[CommandHandler('smartupdate', smart_update_start, filters.User(config.get_chat_ids()))],
        states={
            AI_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, smart_update_process)],
            confirm_state: [MessageHandler(filters.Regex('^(Yes|No)$'), update_end)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
