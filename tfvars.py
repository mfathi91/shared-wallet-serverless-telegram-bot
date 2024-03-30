import sys
import json


def is_letters_only(s):
    return all(c.isalpha() for c in s)


def is_digits_only(s):
    return all(c.isdigit() for c in s)


def main(args):
    """
    This function receives the bot token, usernames, and wallet names as arguments and writes them to terraform.tfvars

    Example of usage: python tfvars.py my_bot_token_12345 Julia,123456 Jack,654321 Dollar,$ Toman,T
    """
    if len(args) < 4:
        print("Usage: tfvars.py <bot_token> <user1> <user2> <wallet1>")
        sys.exit(1)
    if len(args) > 6:
        print("Usage: tfvars.py <bot_token> <user1> <user2> <wallet1> <wallet2> <wallet3>")
        sys.exit(1)

    bot_token = args[0]
    user1 = args[1]
    user2 = args[2]
    wallet1 = args[3]
    wallet2 = None
    if len(args) > 4:
        wallet2 = args[4]
    wallet3 = None
    if len(args) > 5:
        wallet3 = args[5]

    config = {}
    # Validate the input and fill the json_config
    assert isinstance(bot_token, str), "bot_token must be a string"
    config["bot_token"] = bot_token

    assert isinstance(user1, str), "user1 must be a string"
    username1, chat_id1 = user1.split(",")
    assert is_letters_only(username1), "username1 must contain only letters"
    assert is_digits_only(chat_id1), "chat_id1 must contain only digits"
    users = [{"name": username1, "chat_id": int(chat_id1)}]

    assert isinstance(user2, str), "user2 must be a string"
    username2, chat_id2 = user2.split(",")
    assert is_letters_only(username2), "username2 must contain only letters"
    assert is_digits_only(chat_id2), "chat_id2 must contain only digits"
    users.append({"name": username2, "chat_id": int(chat_id2)})
    config["users"] = users

    currency1, symbol1 = wallet1.split(",")
    assert is_letters_only(currency1), "currency1 must contain only letters"
    assert len(symbol1) == 1, "symbol1 must be a single character"
    wallets = [{"currency": currency1, "symbol": symbol1}]

    if wallet2:
        currency2, symbol2 = wallet2.split(",")
        assert is_letters_only(currency2), "currency2 must contain only letters"
        assert len(symbol2) == 1, "symbol2 must be a single character"
        wallets.append({"currency": currency2, "symbol": symbol2})

    if wallet3:
        currency3, symbol3 = wallet3.split(",")
        assert is_letters_only(currency3), "currency3 must contain only letters"
        assert len(symbol3) == 1, "symbol3 must be a single character"
        wallets.append({"currency": currency3, "symbol": symbol3})

    config["wallets"] = wallets

    # Prepare the content of terraform.tfvars
    json_config = json.dumps(config, ensure_ascii=False).replace('"', r'\"')
    content = f'''json_config = "{json_config}"
username1 = "{username1.lower()}"
username2 = "{username2.lower()}"
    '''

    # Write the content to terraform.tfvars
    with open('terraform/terraform.tfvars', 'w') as file:
        file.write(content)


if __name__ == "__main__":
    main(sys.argv[1:])
