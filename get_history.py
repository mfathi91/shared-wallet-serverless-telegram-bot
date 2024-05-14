from configuration import Configuration
from database import Database
from payment import Payment

from pydantic import BaseModel, ValidationError, field_validator
from typing import Dict, List
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
    @classmethod
    def validate_timestamp(cls, value: str):
        try:
            timestamp = date.fromisoformat(value)
            return date.strftime(timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValidationError("Invalid timestamp format")

    @field_validator("wallet")
    @classmethod
    def validate_wallet(cls, wallet_value):
        global wallets
        print(wallet_value)
        if wallet_value not in wallets:
            raise ValidationError(f"Invalid wallet address: {wallet_value}")
        return wallet_value

    @field_validator("payer")
    @classmethod
    def validate_payer(cls, value):
        global users
        if value not in users:
            raise ValidationError(f"Invalid wallet address: {value}")
        return value


def validate_records(records: List[Dict[str, str]]) -> None:
    for record in records:
        try:
            record = Record(**record)
        except ValidationError as e:
            raise ValidationError(f"Invalid dictionary {record}: {e}")


def past_records(input_json: str) -> None:
    config = Configuration()
    database = Database(config)

    try:
        past_records_json = json.loads(input_json)
    except json.JSONDecodeError as e:
        raise ValueError("The input data is not in json format.") from e

    past_records_json = past_records_json.get("payments", [])

    validate_records(past_records_json)

    for record in past_records_json:
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
    users = [sys.argv[2], sys.argv[3]]
    wallets = [sys.argv[4], sys.argv[5], sys.argv[6]]
    past_records(history_json)
