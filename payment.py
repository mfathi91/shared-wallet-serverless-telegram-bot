from __future__ import annotations

import json
from typing import List

import num2persian


class Payment:
    def __init__(self, payer: str, amount: str, wallet: str, wallet_symbol: str, note: str):
        self.payer = payer
        self.amount = amount
        self.wallet = wallet
        self.wallet_symbol = wallet_symbol
        self.note = note

    def format(self) -> str:
        result = f'Payer: {self.payer}\n' \
                 f'Amount: {self.amount} {self.wallet_symbol}\n'
        # TODO: workaround for having Persian amount of payment
        if self.wallet == 'Toman':
            try:
                persian_amount = num2persian.to_persian(self.amount)
                result += f'Amount: {persian_amount}\n'
            except ValueError:
                pass
        result += f'Wallet: {self.wallet}\n' \
                  f'Note: {self.note}\n'
        return result

    def jsonify(self):
        return json.dumps({'payer': self.payer, 'wallet': self.wallet, 'amount': self.amount, 'note': self.note})

    def __repr__(self):
        return f'Payment ({self.payer!r}, {self.amount!r}, {self.wallet!r}, {self.wallet_symbol!r}, {self.note!r})'


class PersistedPayment(Payment):
    def __init__(self, payer: str, amount: str, wallet: str, wallet_symbol: str, note: str, date):
        super().__init__(payer, amount, wallet, wallet_symbol, note)
        self.date = date

    def format(self) -> str:
        return f'{super().format()}Date: {self.date}\n'

    @staticmethod
    def jsonify_all(payments: List[PersistedPayment]) -> str:
        result = {'payments': []}
        for payment in payments:
            result['payments'].append({'payer': payment.payer, 'amount': f'{payment.amount} {payment.wallet_symbol}',
                                       'wallet': payment.wallet, 'note': payment.note, 'datetime': payment.date})
        return json.dumps(result, indent=4)

    def __repr__(self):
        return f'PersistedPayment ({self.payer!r}, {self.amount!r}, {self.wallet!r}, {self.wallet_symbol!r}, {self.note!r}, {self.date!r})'