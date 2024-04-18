from configuration import Configuration
from database import Database
from payment import Payment

import json
import sys


def past_records(input_json: str) -> None:
    config = Configuration()
    database = Database(config)

    try:
        past_records_json = json.loads(input_json)
    except json.JSONDecodeError as e:
        raise ValueError("The input data is not in json format.")

    for record in past_records_json.get("payments", []):
        payer = record.get("payer", "")
        amount = record.get("amount", "")
        wallet = record.get("wallet", "")
        note = record.get("note", "")
        timestamp = record.get("datetime", "")
        wallet_symbol = config.get_wallet_symbol(wallet)

        payment = Payment(
            payer=payer,
            wallet=wallet,
            amount=amount,
            note=note,
            wallet_symbol=wallet_symbol,
        )

        database.add_payment(payment=payment, timestamp=timestamp)


if __name__ == "__main__":
    history_json = sys.argv[1]
    past_records(history_json)
