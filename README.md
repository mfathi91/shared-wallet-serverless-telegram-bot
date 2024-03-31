# Shared wallet telegram bot (serverless)
This is a simple Telegram bot that allows you to create a shared wallet with your friend. In other words, 
if you lend/borrow some money to/from someone, you'd want to keep an eye on how much each person owes the other.
This bot does this accounting for you.

This Telegram bot is serverless, meaning that it doesn't require a server to run it. Amazon AWS lambda functions 
power the execution, hence it is extremely cost-effective (maybe even a few cents per months).

## How to use
1. Make sure you have an AWS account.
2. Create a new Telegram bot using the BotFather. You can find the instructions [here](https://core.telegram.org/bots/tutorial).
3. Fork this repository.
2. Clone this repository.
3. 