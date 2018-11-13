#!/usr/bin/env python3
import os
import numpy as np
import json

import os
import shutil
from trueskill import TrueSkill

import subprocess

for root, dirs, files in os.walk('./replays/'):
    for f in files:
        os.unlink(os.path.join(root, f))
    for d in dirs:
        shutil.rmtree(os.path.join(root, d))

rounds = 20
players = ['MyBot.py', 'Mybot-dev']
wins = np.zeros(len(players))
halite = np.zeros(len(players))

env = TrueSkill(draw_probability=0)
rating_groups = [{player_id: env.create_rating()} for player_id, player in enumerate(players)]

# system_string ='halite.exe --replay-directory replays/ -vvv --width 4 --height 4 --results-as-json ' + '"python " + " python ".join(players)' + ' >> data.gameout'
# print(system_string)
# os.system('halite.exe --replay-directory replays/ --no-logs --width 64 --height 64 --results-as-json --no-timeout '
#           '"pypy3 C:\\Users\Administrator\\Documents\\Halite\\Halite-III\\Halite-Bot\\MyBot.py" '
#           '"pypy3 C:\\Users\Administrator\\Documents\\Halite\\Halite-III\\Halite-Bot-v13\\MyBot-v13.py" '
#           '"pypy3 C:\\Users\Administrator\\Documents\\Halite\\Halite-III\\Halite-Bot-v11\\MyBot-v11.py" '
#           '"pypy3 C:\\Users\Administrator\\Documents\\Halite\\Halite-III\\Halite-Bot\\MyBot.py" >> data.gameout')

try:
    os.remove('data.gameout')
except:
    print()

for i in range(rounds):
    print("Match: {}".format(i))
    os.system('call activate halite')
    os.system('halite.exe --replay-directory replays/ --no-logs --results-as-json '
              '"pypy3 .\\Halite-Bot\\MyBot.py" '
              '"pypy3 .\\Halite-Bot-dev\\MyBot.py" >> data.gameout')
    os.system('call deactivate')

    with open('data.gameout', 'r') as f:
        output = json.load(open("data.gameout"))

        result = [player_stats for player_stats in output['stats']]

        result_rank = [output['stats'][player_id]['rank'] for player_id in result]
        result_halite = [output['stats'][player_id]['score'] for player_id in result]

        wins = np.add(wins, [1 if x is 1 else 0 for x in result_rank])
        halite = np.add(wins, result_halite)
        new_ratings = env.rate(rating_groups, result_rank)
        ratings = [r for r in new_ratings]

    os.remove('data.gameout')

rating_dict = dict((key, env.expose(d[key])) for d in ratings for key in d)

print("Completed")
winrate = wins/rounds
avg_halite = halite/rounds

report = {}
for player_id in range(len(players)):
    report[players[player_id]] = [rating_dict[player_id], winrate[player_id], avg_halite]

print(report)

# for root, dirs, files in os.walk('./replays/'):
#     for f in files:
#         os.unlink(os.path.join(root, f))
#     for d in dirs:
#         shutil.rmtree(os.path.join(root, d))