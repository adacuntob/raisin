import sys
import random
import threading
import time
from collections import defaultdict
from enum import Enum

import config
import bank
import message_queue
from utils import logger

slots_logger = logger("slots")

chips = defaultdict(int)

CHIP_VALUE = 0.01

class Games(Enum):
    EASY = 1
    HARD = 2
    EYY = 3

# Easy slots
EASY_REELS = (
    # S1   S2   S3
    (0.1, 0.2, 0.7), # R1
    (0.1, 0.7, 0.2), # R2
    (0.1, 0.3, 0.6), # R3
)
EASY_SYMBOLS = ("egg", "carrot", "grass")
EASY_PRIZES = (20000, 1000, 420)
EASY_BET = 100

# Cash Machine
EYY_REELS = (
    (0.1,0.9),
    (0.1,0.9),
    (0.1,0.9),
)
EYY_SYMBOLS = ("(_)_)==D~","(.)(.)")
EYY_PRICES = (1000000000,50000000)
EYY_BET = 1

# Hard slots
HARD_REELS = (
    # S1   S2   S3   S4
    (0.1 , 0.45, 0.1 , 0.35), # R1
    (0.1 , 0.2 , 0.25, 0.45), # R2
    (0.05, 0.25, 0.35, 0.35), # R3
)
HARD_SYMBOLS = ("satanium", "weed", "protein", "grape")
HARD_PRIZES = (150000, 10000, 5000, 2500)
HARD_BET = 500

# Games
ongoing_games = set()


def start(sender, channel, game, auto=False):
    if game == Games.EASY:
        reels, symbols, prizes, bet = EASY_REELS, EASY_SYMBOLS, EASY_PRIZES, EASY_BET
    elif game == Games.HARD:
        reels, symbols, prizes, bet = HARD_REELS, HARD_SYMBOLS, HARD_PRIZES, HARD_BET
    elif game == Games.EYY:
        reels, symbols, prizes, bet = EYY_REELS, EYY_SYMBOLS, EYY_PRIZES, EYY_BET
    else:
        message_queue.add(channel, "that game doesn't exist")
        return

    current_chips = chips[sender]
    if chips[sender] < bet:
        message_queue.add(channel, "you only have {} chips, this game requires {} per play".format(current_chips, bet))
        return

    if sender in ongoing_games:
        message_queue.add(channel, "calm down")
        return
    
    if auto:
        player_thread = threading.Thread(target=auto_play, args=(sender, channel, reels, symbols, prizes, bet))
        ongoing_games.add(sender)
        player_thread.start()
    else:
        single_play(sender, channel, reels, symbols, prizes, bet)


def single_play(sender, channel, reels, symbols, prizes, bet):
    chips[sender] -= bet
    roll = slot_roll(sender, channel, reels, symbols)
    pay_prizes(sender, channel, roll, prizes, symbols)


def auto_play(sender, channel, reels, symbols, prizes, bet):
    slots_logger.info(f"{sender} started auto-play with {chips[sender]} chips")
    while chips[sender] >= bet and sender in ongoing_games:
        single_play(sender, channel, reels, symbols, prizes, bet)
        time.sleep(0.6)
    sys.exit()


def stop(sender, channel):
    if sender in ongoing_games:
        ongoing_games.remove(sender)
        slots_logger.info(f"{sender} stopped auto-play with {chips[sender]} chips")
        message_queue.add(channel, "why'd you stop, gentile")


def slot_roll(sender, channel, reels, symbols):
    chips_left = chips[sender]
    roll = [random.choices(symbols, reel_probs)[0] for reel_probs in reels]
    text_result = "[{}], {} chips left".format(" - ".join(roll), chips_left)
    message_queue.add(channel, text_result)
    return roll


def pay_prizes(sender, channel, roll, prizes, symbols):
    for index, symbol in enumerate(symbols):
        if set(roll) == set([symbol]):
            prize = prizes[index]
            message_queue.add(channel, "{}x3, won {} chips".format(symbol, prize))
            chips[sender] += prize
            return


# Money
def buy_chips(sender, channel, amount):
    if bank.transfer_money(sender, config.nickname, amount * CHIP_VALUE):
        slots_logger.info(f"{sender} bought {amount} chips")
        message_queue.add(channel, f"{sender} bought {amount} chips")
    else:
        return

    chips[sender] += amount


def cash_out(sender, channel):
    if chips[sender] == 0:
        message_queue.add(channel, "nothing to cash out")
        return

    current_chips = chips[sender]
    amount = current_chips * CHIP_VALUE
    bank.transfer_money(config.nickname, sender, amount)
    chips[sender] = 0
    slots_logger.info(f"{sender} cashed out {current_chips} chips, {amount:.2f} bux")
    message_queue.add(sender, f"you got {amount:.2f} newbux from slots")

