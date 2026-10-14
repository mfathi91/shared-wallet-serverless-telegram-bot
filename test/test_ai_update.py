import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_update import extract_payment, validate
from configuration import Configuration

VALID_CFG_JSON = '{"bot_token": "my_bot_token",' \
                 '"wallets": [{"currency": "Dollar", "symbol": "$"}, {"currency": "Toman", "symbol": "T"}],' \
                 '"users": [{"name": "Julia", "chat_id": 1234}, {"name": "Jack", "chat_id": 4321}]}'


def gemini_response(fields: dict) -> MagicMock:
    """Fake httpx response carrying a canned Gemini generateContent payload."""
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        'candidates': [{'content': {'parts': [{'text': json.dumps(fields, ensure_ascii=False)}]}}]
    }
    return response


class TestValidate(unittest.TestCase):

    def setUp(self):
        os.environ["JSON_CONFIG"] = VALID_CFG_JSON
        self.config = Configuration()

    def test_valid_fields(self):
        clean, missing = validate({'wallet': 'Toman', 'payer': 'Jack', 'amount': '250000', 'note': 'dinner'},
                                  self.config)
        self.assertEqual([], missing)
        self.assertEqual({'wallet': 'Toman', 'payer': 'Jack', 'amount': '250000', 'note': 'dinner'}, clean)

    def test_amount_with_cents_is_valid(self):
        _, missing = validate({'wallet': 'Dollar', 'payer': 'Julia', 'amount': '40.50'}, self.config)
        self.assertEqual([], missing)

    def test_missing_amount(self):
        _, missing = validate({'wallet': 'Dollar', 'payer': 'Julia', 'amount': None}, self.config)
        self.assertEqual(['amount'], missing)

    def test_missing_wallet(self):
        _, missing = validate({'wallet': None, 'payer': 'Julia', 'amount': '10'}, self.config)
        self.assertEqual(['wallet'], missing)

    def test_missing_payer(self):
        _, missing = validate({'wallet': 'Dollar', 'payer': None, 'amount': '10'}, self.config)
        self.assertEqual(['payer'], missing)

    def test_wallet_not_in_config(self):
        _, missing = validate({'wallet': 'Euro', 'payer': 'Julia', 'amount': '10'}, self.config)
        self.assertEqual(['wallet'], missing)

    def test_payer_not_in_config(self):
        _, missing = validate({'wallet': 'Dollar', 'payer': 'Bob', 'amount': '10'}, self.config)
        self.assertEqual(['payer'], missing)

    def test_amount_with_comma_is_invalid(self):
        _, missing = validate({'wallet': 'Toman', 'payer': 'Julia', 'amount': '250,000'}, self.config)
        self.assertEqual(['amount'], missing)

    def test_amount_non_numeric_is_invalid(self):
        _, missing = validate({'wallet': 'Toman', 'payer': 'Julia', 'amount': 'abc'}, self.config)
        self.assertEqual(['amount'], missing)

    def test_all_missing(self):
        _, missing = validate({'wallet': None, 'payer': None, 'amount': None, 'note': None}, self.config)
        self.assertEqual(['wallet', 'payer', 'amount'], missing)

    def test_null_note_defaults_to_dash(self):
        clean, missing = validate({'wallet': 'Dollar', 'payer': 'Julia', 'amount': '10', 'note': None}, self.config)
        self.assertEqual([], missing)
        self.assertEqual('-', clean['note'])

    def test_empty_note_defaults_to_dash(self):
        clean, _ = validate({'wallet': 'Dollar', 'payer': 'Julia', 'amount': '10', 'note': '   '}, self.config)
        self.assertEqual('-', clean['note'])

    def test_whitespace_is_stripped(self):
        clean, missing = validate({'wallet': ' Dollar ', 'payer': 'Julia\n', 'amount': ' 10 ', 'note': ' taxi '},
                                  self.config)
        self.assertEqual([], missing)
        self.assertEqual({'wallet': 'Dollar', 'payer': 'Julia', 'amount': '10', 'note': 'taxi'}, clean)


class TestExtractPayment(unittest.TestCase):

    def setUp(self):
        os.environ["JSON_CONFIG"] = VALID_CFG_JSON
        self.config = Configuration()

    def _run(self, text, sender, response, env=None):
        env = {'GEMINI_API_KEY': 'test-key'} if env is None else env
        with patch.dict(os.environ, env, clear=False), \
                patch('httpx.AsyncClient.post', new_callable=AsyncMock, return_value=response) as post:
            if not env.get('GEMINI_MODEL'):
                os.environ.pop('GEMINI_MODEL', None)
            result = asyncio.run(extract_payment(text, sender, self.config))
        return result, post

    def test_extract_returns_fields(self):
        response = gemini_response({'wallet': 'Toman', 'payer': 'Jack', 'amount': '250000', 'note': 'شام'})
        result, post = self._run('۲۵۰ هزار تومن من برای شام دادم', 'Jack', response)
        self.assertEqual({'wallet': 'Toman', 'payer': 'Jack', 'amount': '250000', 'note': 'شام'}, result)
        post.assert_awaited_once()

    def test_extract_missing_fields_are_none(self):
        response = gemini_response({'wallet': None, 'payer': None, 'amount': None, 'note': 'شام'})
        result, _ = self._run('برای شام پول دادم', 'Jack', response)
        self.assertIsNone(result['wallet'])
        self.assertIsNone(result['payer'])
        self.assertIsNone(result['amount'])

    def test_request_uses_api_key_header_and_default_model(self):
        response = gemini_response({'wallet': 'Dollar', 'payer': 'Julia', 'amount': '40', 'note': None})
        _, post = self._run('Jack paid 40 dollars for taxi', 'Julia', response)
        args, kwargs = post.call_args
        url = args[0] if args else kwargs['url']
        self.assertEqual(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent', url)
        self.assertEqual('test-key', kwargs['headers']['x-goog-api-key'])
        self.assertNotIn('test-key', url)
        generation_config = kwargs['json']['generationConfig']
        self.assertEqual('application/json', generation_config['responseMimeType'])
        self.assertEqual(0, generation_config['temperature'])
        self.assertTrue(generation_config['responseSchema']['properties']['note']['nullable'])

    def test_model_can_be_overridden_by_env(self):
        response = gemini_response({'wallet': 'Dollar', 'payer': 'Julia', 'amount': '40', 'note': None})
        _, post = self._run('text', 'Julia', response, env={'GEMINI_API_KEY': 'k', 'GEMINI_MODEL': 'gemini-test'})
        args, kwargs = post.call_args
        url = args[0] if args else kwargs['url']
        self.assertTrue(url.endswith('/models/gemini-test:generateContent'))

    def test_malformed_response_raises(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {'candidates': []}
        with self.assertRaises(Exception):
            self._run('text', 'Julia', response)


if __name__ == '__main__':
    unittest.main()
