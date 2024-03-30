import os
import unittest
from json import JSONDecodeError

from configuration import Configuration, ConfigurationError


class TestConfiguration(unittest.TestCase):

    VALID_CFG_JSON = '{"bot_token": "my_bot_token",' \
                     '"wallets": [{"currency": "Dollar", "symbol": "$"}, {"currency": "Toman", "symbol": "T"}],' \
                     '"users": [{"name": "Julia", "chat_id": 1234}, {"name": "Jack", "chat_id": 4321}]}'

    # --------------__init__--------------
    def test_init(self):
        # Should fail because the JSON is invalid
        os.environ["JSON_CONFIG"] = ('{"bot_token": "foo", wallets": : "Dollar", "symbol": "$"}],"users": [": 1234}, '
                                     '{"name": "Jack", "chat_id": 4321}]}')
        with self.assertRaises(JSONDecodeError):
            Configuration()

    def test_init2(self):
        # Should fail because no wallets is configured
        os.environ["JSON_CONFIG"] = ('{"bot_token": "foo",'
                           '"users": [{"name": "Julia", "chat_id": 1234}, {"name": "Jack", "chat_id": 4321}]}')
        with self.assertRaises(KeyError) as cm:
            Configuration()
        self.assertEqual("'wallets'", str(cm.exception))

    def test_init3(self):
        # Should fail because no users is configured
        os.environ["JSON_CONFIG"] = ('{"bot_token": "foo",'
                           '"wallets": [{"currency": "Dollar", "symbol": "$"}]}')
        with self.assertRaises(KeyError) as cm:
            Configuration()
        self.assertEqual("'users'", str(cm.exception))

    def test_init4(self):
        # Should fail because of similar currency names
        os.environ["JSON_CONFIG"] = ('{"bot_token": "foo",'
                           '"wallets": [{"currency": "Dollar", "symbol": "$"}, {"currency": "Dollar", "symbol": "T"}],'
                           '"users": [{"name": "Julia", "chat_id": 1234}, {"name": "Jack", "chat_id": 4321}]}')
        with self.assertRaises(ConfigurationError) as cm:
            Configuration()
        self.assertEqual('Configuration error: the wallet must have unique currency names.', str(cm.exception))

    def test_init5(self):
        # Should fail because number of configured users is not 2
        os.environ["JSON_CONFIG"] = ('{"bot_token": "foo",'
                           '"wallets": [{"currency": "Dollar", "symbol": "$"}],'
                           '"users": [{"name": "Julia", "chat_id": 1234}]}')
        with self.assertRaises(ConfigurationError) as cm:
            Configuration()
        self.assertEqual('Configuration error: number of configured users must be 2, while it is 1', str(cm.exception))

    def test_init6(self):
        # Should fail because type of username is not str
        os.environ["JSON_CONFIG"] = ('{"bot_token": "my_bot_token",'
                           '"wallets": [{"currency": "Dollar", "symbol": "$"}, {"currency": "Toman", "symbol": "T"}],'
                           '"users": [{"name": 6543, "chat_id": 1234}, {"name": "Jack", "chat_id": 4321}]}')
        with self.assertRaises(ConfigurationError) as cm:
            Configuration()
        self.assertEqual('Type of the configured usernames is not str', str(cm.exception))

    def test_init7(self):
        # Should fail because type of chat id is not int
        os.environ["JSON_CONFIG"] = ('{"bot_token": "my_bot_token",'
                           '"wallets": [{"currency": "Dollar", "symbol": "$"}, {"currency": "Toman", "symbol": "T"}],'
                           '"users": [{"name": "Julia", "chat_id": "1234"}, {"name": "Jack", "chat_id": 4321}]}')
        with self.assertRaises(ConfigurationError) as cm:
            Configuration()
        self.assertEqual('Type of the configured chat IDs is not int', str(cm.exception))

    def test_init8(self):
        # Should create the new instance successfully
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        Configuration()

    # --------------get_token()--------------
    def test_get_token(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        self.assertEqual('my_bot_token', Configuration().get_token())

    # --------------get_usernames()--------------
    def test_get_usernames(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        self.assertEqual(['Julia', 'Jack'], Configuration().get_usernames())

    # --------------get_other_username()--------------
    def test_get_other_username(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        config = Configuration()
        self.assertEqual('Julia', config.get_other_username('Jack'))
        self.assertEqual('Jack', config.get_other_username('Julia'))

    def test_get_other_username2(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        non_existing_username = 'Non_Existing_User'
        with self.assertRaises(ValueError, msg=f'Unable to find other username of: {non_existing_username}'):
            Configuration().get_other_username(non_existing_username)

    # --------------get_chat_ids()--------------
    def test_get_chat_ids(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        self.assertEqual([1234, 4321], Configuration().get_chat_ids())

    # --------------get_chat_id()--------------
    def test_get_chat_id(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        config = Configuration()
        self.assertEqual(1234, config.get_chat_id('Julia'))
        self.assertEqual(4321, config.get_chat_id('Jack'))

    def test_get_chat_id2(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        non_existing_username = 'Non_Existing_User'
        with self.assertRaises(ValueError, msg=f'Unable to find other username of: {non_existing_username}'):
            Configuration().get_chat_id(non_existing_username)

    # --------------get_other_chat_id()--------------
    def test_get_other_chat_id(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        config = Configuration()
        self.assertEqual(4321, config.get_other_chat_id(1234))
        self.assertEqual(1234, config.get_other_chat_id(4321))

    def test_get_other_chat_id2(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        non_existing_chat_id = 8765
        with self.assertRaises(ValueError, msg=f'Unable to find other chat_id of: {non_existing_chat_id}'):
            Configuration().get_other_chat_id(non_existing_chat_id)

    # --------------get_currencies()--------------
    def test_get_currencies(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        self.assertEqual(['Dollar', 'Toman'], Configuration().get_currencies())

    # --------------get_wallet_symbol()--------------
    def test_get_wallet_symbol(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        config = Configuration()
        self.assertEqual('$', config.get_wallet_symbol('Dollar'))
        self.assertEqual('T', config.get_wallet_symbol('Toman'))

    def test_get_wallet_symbol2(self):
        os.environ["JSON_CONFIG"] = TestConfiguration.VALID_CFG_JSON
        non_existing_currency = 'NonExistingCurrency'
        with self.assertRaises(ValueError, msg=f'Unknown currency {non_existing_currency}'):
            Configuration().get_wallet_symbol(non_existing_currency)
