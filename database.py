import os
from dataclasses import dataclass
from datetime import datetime
from typing import List

import boto3
from boto3.dynamodb.conditions import Key

from configuration import Configuration
from payment import Payment, PersistedPayment


@dataclass(frozen=True)
class Balance:
    creditor: str
    debtor: str
    amount: str


class Database:

    def __init__(self, configuration: Configuration):
        self._configuration = configuration
        dynamodb = boto3.resource("dynamodb")
        self._table = dynamodb.Table(f"table-sw-{'-'.join(configuration.get_usernames()).lower()}-payments")

    def add_payment(self, payment: Payment):
        self._table.put_item(Item={
            "wallet": payment.wallet,
            "timestamp": datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'),
            "payer": payment.payer,
            "amount": payment.amount,
            "note": payment.note
        })

    def get_payments(self, wallet: str = None) -> List[PersistedPayment]:
        payments: List[PersistedPayment] = []
        if wallet:
            response = self._table.query(KeyConditionExpression=Key('wallet').eq(wallet))
        else:
            response = self._table.scan()
        
        sorted_response = sorted(response.get("Items", []), key=lambda x: datetime.strptime(x.get("timestamp"), '%Y-%m-%d %H:%M:%S'))
        for item in sorted_response:
            payments.append(PersistedPayment(item.get("payer"),
                                             item.get("amount"), item.get("wallet"),
                                             self._configuration.get_wallet_symbol(item.get("wallet")),
                                             item.get("note"),
                                             item.get("timestamp")))
        return payments

    def get_balance(self, wallet: str) -> Balance:
        user1, balance1 = self._configuration.get_usernames()[0], 0
        for payment in self.get_payments(wallet):
            balance1 = balance1 + float(payment.amount) if payment.payer == user1 else balance1 - float(payment.amount)
        if balance1 == 0:
            return Balance(creditor=user1, debtor=self._configuration.get_other_username(user1), amount='0')
        elif balance1 > 0:
            return Balance(creditor=user1, debtor=self._configuration.get_other_username(user1), amount=str(round(balance1, 2)).rstrip('0').rstrip('.'))
        else:
            return Balance(creditor=self._configuration.get_other_username(user1), debtor=user1, amount=str(round(-balance1, 2)).rstrip('0').rstrip('.'))
