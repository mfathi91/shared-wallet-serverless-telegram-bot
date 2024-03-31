import asyncio
import json
import logging
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    filters,
    MessageHandler
)

import num2persian
from configuration import Configuration
from database import Database
from payment import Payment, PersistedPayment

# Create and initialize the configuration
config = Configuration()

# Create and initialize the database
database = Database(config)

# Build the application
application = Application.builder().token(config.get_token()).build()

# State of the conversations
WALLET, PAYER, NOTE, AMOUNT, CONFIRM = range(5)
WALLET_BALANCE = 5


# ------------------ start command --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /start command", update.message.from_user.first_name)
    await update.message.reply_text(
        'Hi 👋, this is a simple bot to manage your shared expenses with another person. These are the available commands:\n'
        '/update - update a wallet\n'
        '/status - show the status of a wallet\n'
        '/last5 - show the last 5 payments\n'
        '/history - get the full history as a file\n'
        '/cancel - cancel the current operation'
    )
    return ConversationHandler.END


# ------------------- update conversation functions -------------------
async def update_choose_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /update command", update.message.from_user.first_name)
    reply_keyboard = [config.get_currencies()]
    await update.message.reply_text(
        'Which wallet do you want to change?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return WALLET


async def update_choose_payer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data['wallet'] = update.message.text
    reply_keyboard = [config.get_usernames()]
    await update.message.reply_text(
        text='Whose balance to increase?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return PAYER


async def update_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data['payer'] = update.message.text
    await update.message.reply_text(
        text=f'Ok.\nHow many {context.chat_data["wallet"]}s?',
        reply_markup=ReplyKeyboardRemove(),
    )
    return AMOUNT


async def update_enter_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data['amount'] = update.message.text
    await update.message.reply_text(
        text='Ok.\nDo you have a note for this payment? If not, enter /skip .',
        reply_markup=ReplyKeyboardRemove(),
    )
    return NOTE


async def update_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    note_input = update.message.text
    context.chat_data['note'] = '-' if note_input == '/skip' else note_input

    cd = context.chat_data
    payment = Payment(cd['payer'], cd['amount'], cd['wallet'], config.get_wallet_symbol(cd['wallet']), cd['note'])
    cd['payment'] = payment
    reply_keyboard = [['Yes', 'No']]
    await update.message.reply_text(
        text=f'Do you confirm the following payment?\n{payment.format()}',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder='Yes or No'),
    )
    return CONFIRM


async def update_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == 'Yes':
        payment = context.chat_data['payment']
        logging.info('User %s finalized /update command. Parameters: %s', update.message.from_user.first_name,
                     payment.jsonify())
        database.add_payment(payment)
        await update.message.reply_text(
            get_formatted_balance(payment.wallet),
            reply_markup=ReplyKeyboardRemove(),
        )

        # Inform the other user about the payment
        other = config.get_other_chat_id(update.message.chat_id)
        msg = f'{payment.format()}\n' \
              f'New status:\n' \
              f'{get_formatted_balance(payment.wallet)}'
        await application.bot.send_message(
            chat_id=other,
            text=msg
        )
    else:
        await update.message.reply_text(
            'Ok, the process is canceled.',
            reply_markup=ReplyKeyboardRemove(),
        )
    return ConversationHandler.END


# ------------------ status conversation --------------------
async def status_choose_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /status command", update.message.from_user.first_name)
    reply_keyboard = [config.get_currencies()]
    await update.message.reply_text(
        'Which wallet do you want to see?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    return WALLET_BALANCE


async def status_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    wallet = update.message.text
    await update.message.reply_text(
        get_formatted_balance(wallet),
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ------------------ history command --------------------
async def history_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /history command", update.message.from_user.first_name)
    history_json = f'/tmp/{datetime.now()}.json'
    with open(history_json, 'w') as f:
        f.write(PersistedPayment.jsonify_all(database.get_payments()))
    await update.message.reply_document(
        document=history_json,
        filename='history.json'
    )
    return ConversationHandler.END


# ----------- cancel current operation for all the conversations -------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /cancel command", update.message.from_user.first_name)
    context.chat_data.clear()
    await update.message.reply_text(
        'Ok, the process is canceled.', reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ------------------ last 5 command --------------------
async def last_5_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("User %s issued /last5 command", update.message.from_user.first_name)
    payments = database.get_payments()[-5:]
    if payments:
        msg = ''
        for payment in payments:
            msg += f'{payment.format()}\n'
    else:
        msg = 'No payments registered'
    await update.message.reply_text(text=msg)
    return ConversationHandler.END


def lambda_handler(event, context):
    return asyncio.get_event_loop().run_until_complete(main(event, context))


# --------------------- Utility methods -----------------------
def get_formatted_balance(wallet: str) -> str:
    balance = database.get_balance(wallet)
    if balance:
        if balance.amount != '0':
            symbol = config.get_wallet_symbol(wallet)
            if wallet == 'Toman':
                return (f'{balance.creditor}: {balance.amount} {symbol}'
                        f'\n{num2persian.to_persian(str(int(float(balance.amount))))}'
                        f'\n{balance.debtor}: 0 {symbol}')
            return f'{balance.creditor}: {balance.amount} {symbol}\n{balance.debtor}: 0 {symbol}'
    return '0'


async def main(event, context):
    # Skip if event body is not there
    event_body = event.get("body")
    if not event_body:
        return {
            'statusCode': 500,
            'body': 'event body not available'
        }

    # Add command handler for the start command
    application.add_handler(CommandHandler('start', start, filters.User(config.get_chat_ids())))

    # Add command handler to get the last 5 payments (regardless of the wallets)
    application.add_handler(CommandHandler('last5', last_5_payments, filters.User(config.get_chat_ids())))

    # Add command handler to get the full history of the payments
    application.add_handler(CommandHandler('history', history_payments, filters.User(config.get_chat_ids())))

    # Add conversation handler for updating a wallet
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('update', update_choose_wallet, filters.User(config.get_chat_ids()))],
        states={
            WALLET: [MessageHandler(filters.Regex(f'^({"|".join(config.get_currencies())})$'), update_choose_payer)],
            PAYER: [MessageHandler(filters.Regex(f'^({"|".join(config.get_usernames())})$'), update_enter_amount)],
            AMOUNT: [MessageHandler(filters.Regex('^[0-9]+(.[0-9]{2})?$') & ~filters.COMMAND, update_enter_note)],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_confirm),
                   CommandHandler('skip', update_confirm)],
            CONFIRM: [MessageHandler(filters.Regex('^(Yes|No)$'), update_end)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    ))

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('status', status_choose_wallet, filters.User(config.get_chat_ids()))],
        states={
            WALLET_BALANCE: [MessageHandler(filters.Regex(f'^({"|".join(config.get_currencies())})$'), status_end)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    ))

    try:
        await application.initialize()
        await application.process_update(Update.de_json(json.loads(event["body"]), application.bot))
        return {
            'statusCode': 200,
            'body': 'Success'
        }
    except Exception as ex:
        logging.error("An error occurred: %s", str(ex))
        return {
            'statusCode': 500,
            'body': f'Failure: {str(ex)}'
        }
