import json
import os
from typing import List, Dict
import logging


class Configuration:

    def __init__(self):
        data = json.loads(os.environ["JSON_CONFIG"])
        logging.info(f'ENV VARIABLE JSON_CONFIG: {data}')
        self.token = data['bot_token']

        # Initialize wallets
        self._wallets: List[Dict[str, str]] = data['wallets']
        currencies = [w['currency'] for w in self._wallets]
        if len(set(currencies)) < len(currencies):
            raise ConfigurationError('Configuration error: the wallet must have unique currency names.')

        # Validate and initialize users
        self._users = data['users']
        if len(self._users) != 2:
            raise ConfigurationError(
                f'Configuration error: number of configured users must be 2, while it is {len(self._users)}')
        self._user1 = data['users'][0]
        self._user2 = data['users'][1]
        if 'name' not in self._user1 or 'name' not in self._user2:
            raise ConfigurationError('Configuration error: "name" not defined in at least one user.')
        if 'chat_id' not in self._user1 or 'chat_id' not in self._user2:
            raise ConfigurationError('Configuration error: "chat_id" not defined in at least one user.')
        if self._user1['name'] == self._user2['name']:
            raise ConfigurationError('Configuration error: usernames cannot be the same.')
        if type(self._user1['name']) != str or type(self._user2['name']) != str:
            raise ConfigurationError('Type of the configured usernames is not str')
        if type(self._user1['chat_id']) != int or type(self._user2['chat_id']) != int:
            raise ConfigurationError('Type of the configured chat IDs is not int')

        logging.info(f'Configured users: {self._user1["name"]} and {self._user2["name"]}')
        logging.info(f'Configured user IDs: {self._user2["chat_id"]} and {self._user2["chat_id"]}')

    def get_token(self) -> str:
        return self.token

    def get_usernames(self) -> List[str]:
        return [self._user1['name'], self._user2['name']]

    def get_other_username(self, username: str) -> str:
        if username == self._user1['name']:
            return self._user2['name']
        elif username == self._user2['name']:
            return self._user1['name']
        else:
            raise ValueError(f'Unable to find other username of: {username}')

    def get_chat_ids(self) -> List[int]:
        return [self._user1['chat_id'], self._user2['chat_id']]

    def get_chat_id(self, username) -> int:
        if username == self._user1['name']:
            return self._user1['chat_id']
        elif username == self._user2['name']:
            return self._user2['chat_id']
        else:
            raise ValueError(f'Unable to find other username of: {username}')

    def get_other_chat_id(self, chat_id: int) -> str:
        if chat_id == self._user1['chat_id']:
            return self._user2['chat_id']
        elif chat_id == self._user2['chat_id']:
            return self._user1['chat_id']
        else:
            raise ValueError(f'Unable to find other chat_id of: {chat_id}')

    def get_currencies(self) -> List[str]:
        return [w['currency'] for w in self._wallets]

    def get_wallet_symbol(self, currency: str) -> str:
        for w in self._wallets:
            if w['currency'] == currency:
                return w['symbol']
        raise ValueError(f'Unknown currency {currency}')


class ConfigurationError(ValueError):
    pass
