import sys
import random
import importlib
import urllib

import config
import message_queue
import wikipedia
import wolfram
import bank
import grass
import slots
from irc_common import users, execute
from calc import calculate
from utils import requests_session, random_quote, is_number, pastebin, sprunge

# Run user commands
def run_command(message_data):
    sender = message_data["sender"]
    full_text = message_data["full_text"]
    # "#channel" if room, "sender" if private message
    channel = message_data["channel"]
    command = message_data["command"]
    args = message_data["args"]

    # Reply to mention with a random quote
    if config.nickname in full_text:
        message_queue.add(channel, random_quote(sender))

    if len(full_text) > 10:
        bank.make_money(sender)

    ## IRC commands ##
    def cringe_words(message):
        for w in ["xd", "spic", "cring", "derail"]:
            if w in "".join(c for c in "".join(message.lower().split()) if c.isalpha()): return True
        return False

    if sender == "eyy" and cringe_words(full_text):
        execute("KICK #bogota eyy ebin")

    search_term = None
    if args:
        search_term = urllib.parse.quote_plus(" ".join(args))
    
    if not command:
        return

    elif command == "help":
        message_queue.add(sender, "Search engines: google, wa, ddg, drae, dpd, en, es")
        message_queue.add(sender, "Misc: pick [list], roll (number), ask (query), fetch (wikipedia_article), calc (expression), bux, sendbux (user) (amount)")
        message_queue.add(sender, "Grass: grass-new (chip-value), grass-start, grass-join, gr, gb (amount), gp, gs, grass-cancel")
        message_queue.add(sender, "Slots: slot-chips (amount), easy-slot <auto>, hard-slot <auto>, slot-stop, slot-cashout")

    # Google
    elif command == "google":
        message_queue.add(channel, "https://www.google.com/search?q={}".format(search_term))
        
    # Wolfram Alpha
    elif command == "wa":
        message_queue.add(channel, "http://www.wolframalpha.com/input/?i={}".format(search_term))

    # DuckDuckGo
    elif command == "ddg":
        message_queue.add(channel, "http://duckduckgo.com/?q={}".format(search_term))

    # DRAE
    elif command == "drae":
        message_queue.add(channel, "http://lema.rae.es/drae/?val={}".format(search_term))

    # DPD
    elif command == "dpd":
        message_queue.add(channel, "http://lema.rae.es/dpd/?key={}".format(search_term))

    # Jisho kanji lookup
    elif command == "kan":
        message_queue.add(channel, "http://jisho.org/kanji/details/{}".format(search_term))

    # EN > JP
    elif command == "ei":
        message_queue.add(channel, "http://jisho.org/words?jap=&eng={}&dict=edict".format(search_term))

    # JP > EN
    elif command == "ni":
        message_queue.add(channel, "http://jisho.org/words?jap={}&eng=&dict=edict".format(search_term))

    # EN > ES
    elif command == "en":
        message_queue.add(channel, "http://www.wordreference.com/es/translation.asp?tranword={}".format(search_term))

    # ES > EN
    elif command == "es":
        message_queue.add(channel, "http://www.wordreference.com/es/en/translation.asp?spen={}".format(search_term))

    # Random choice
    elif command == "pick":
        if len(args) > 1:
            message_queue.add(channel, random.choice(args))

    # Die roll
    elif command == "roll":
        if not args:
            max_roll = 6
        elif len(args) == 1 and args[0].isdigit():
            max_roll = int(args[0])
        
        message_queue.add(channel, random.randint(1, max_roll))

    # Wolfram Alpha query
    elif command == "ask":
        response = wolfram.ask(" ".join(args))
        message_queue.add(channel, response)

    # Calculator
    elif command == "calc":
        expression = ''.join(args)
        result = str(calculate(expression))
        message_queue.add(channel, result)

    # Wikipedia fetch
    elif command == "fetch":
        article_name = ' '.join(args)
        extract = wikipedia.fetch(article_name)
        message_queue.add(channel, extract)

    # Check balance
    elif command == "bux":
        amount = bank.ask_money(sender)
        message_queue.add(channel, "{} has {:.2f} newbux".format(sender, amount))

    # Transfer money
    elif command == "sendbux":
        if len(args) != 2:
            message_queue.add(channel, "eh")
            return
        source, destination, amount = sender, args[0], args[1]
        if not is_number(amount):
            message_queue.add(source, "numbers please")
            return
        bank.transfer_money(source, destination, float(amount))

    # Grass game 
    elif command == "grass-new":
        if len(args) < 1:
            message_queue.add(channel, "how much for each chip")
            return
        chip_value = args[0]
        if not is_number(chip_value):
            message_queue.add(source, "numbers please")
            return
        grass.new_game(sender, channel, float(chip_value))

    elif command == "grass-join":
        grass.add_player(sender, channel)

    elif command == "grass-start":
        grass.start(sender, channel)

    elif command == "gr":
        grass.play(sender, channel)

    elif command == "gb":
        if len(args) < 1:
            message_queue.add(channel, "how much are you betting")
            return
        bet = args[0]
        if not is_number(bet):
            message_queue.add(channel, "numbers please")
            return
        grass.bet(sender, bet, channel)

    elif command == "gp":
        grass.pass_turn(sender, channel)

    elif command == "gs":
        grass.print_chips(channel)

    elif command == "grass-cancel":
        grass.abort(channel)

    # Slot machine
    elif command == "slot-chips":
        if len(args) < 1:
            message_queue.add(channel, "how many are you buying")
            return
        amount = args[0]
        if not is_number(amount):
            message_queue.add(channel, "numbers please")
            return
        slots.buy_chips(sender, channel, int(amount))

    elif command == "easy-slot":
        auto = False
        if len(args) == 1 and args[0] == "auto":
            auto = True
        slots.start(sender, channel, slots.Games.EASY, auto=auto)

    elif command == "hard-slot":
        auto = False
        if len(args) == 1 and args[0] == "auto":
            auto = True
        slots.start(sender, channel, slots.Games.HARD, auto=auto)

    elif command == "slot-stop":
        slots.stop(sender, channel)

    elif command == "slot-cashout":
        slots.cash_out(sender, channel)

    ## Owner commands ##
    if sender == config.owner:
        # Disconnect
        if command == "quit":
            execute("QUIT")
            sys.exit(0)

        # Send message from bot
        elif command == "say":
            if len(args) > 1:
                message = ' '.join(args[1:])
                message_queue.add(args[0], message)

        # Print userlist
        elif command == "users":
            message_queue.add(channel, str(irc_common.users))

        # Bot joins
        elif command == "join":
            channel = args[0]
            execute("JOIN %s" % channel)

        # Bot parts
        elif command == "part":
            execute("PART %s" % channel)
            del users[channel]

        # Bot kicks
        elif command == "kick":
            user = args[0]
            reason = " ".join(args[1:])
            if not reason:
                reason = "huh"
            bot_kick(channel, user, reason)

        # Module reloads
        elif command == "reload":
            module_name = args[0]
            importlib.reload(sys.modules[module_name])
            message_queue.add(channel, "aight")
