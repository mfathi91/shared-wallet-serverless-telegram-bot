from configuration import Configuration
from database import Database
from payment import Payment

from pydantic import BaseModel, ValidationError, field_validator
from datetime import datetime as date
import json
import sys


class Record(BaseModel):
    payer: str
    amount: str
    wallet: str
    note: str
    datetime: str

    @field_validator("datetime")
    def validate_timestamp(cls, value):
        try:
            timestamp = date.fromisoformat(value)
            return date.strftime(timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValidationError("Invalid timestamp format")


def past_records(input_json: str) -> None:
    config = Configuration()
    database = Database(config)

    try:
        past_records_json = json.loads(input_json)
    except json.JSONDecodeError as e:
        raise ValueError("The input data is not in json format.")

    for record in past_records_json.get("payments", []):
        try:
            record = Record(**record)
        except ValidationError as e:
            print(f"Invalid dictionary {record}: {e}")
            continue

        payer = record["payer"]
        amount = record["amount"]
        wallet = record["wallet"]
        note = record["note"]
        timestamp = record["datetime"]
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
