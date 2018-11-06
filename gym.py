#!/usr/bin/env python3
import os
import numpy as np
import json

import os
import shutil
from trueskill import TrueSkill

rounds = 5
players = ['MyBot.py', 'MyOldBot.py']
wins = np.zeros(len(players))

env = TrueSkill(draw_probability=0)
rating_groups = [{player_id: env.create_rating()} for player_id, player in enumerate(players)]

system_string ='halite.exe --replay-directory replays/ -vvv --width 4 --height 4 --results-as-json ' + '"python " + " python ".join(players)' + ' >> data.gameout'
print(system_string)

for i in range(rounds):
    print("Match: {}".format(i))
    os.system('call activate halite')
    os.system('halite.exe --replay-directory replays/ -vvv --width 4 --height 4 --results-as-json "python MyBot.py" "python MyBot.py" >> data.gameout')
    os.system('call deactivate')

    with open('data.gameout', 'r') as f:
        output = json.load(open("data.gameout"))

        result = [player_stats for player_stats in output['stats']]

        result_rank = [output['stats'][player_id]['rank'] - 1 for player_id in result]
        result_halite = [output['stats'][player_id]['score'] for player_id in result]

        wins = np.add(wins, result_rank)

        new_ratings = env.rate(rating_groups, result_rank)
        ratings = [r for r in new_ratings]

    os.remove('data.gameout')


rating_dict = dict((key, env.expose(d[key])) for d in ratings for key in d)

print("Completed")
print(rating_dict)
print(ratings)
winrate = 1-wins/rounds

report = {}
for player_id in range(len(players)):
    report[player_id] = [rating_dict[player_id], winrate[player_id]]

print(report)

for root, dirs, files in os.walk('./replays/'):
    for f in files:
        os.unlink(os.path.join(root, f))
    for d in dirs:
        shutil.rmtree(os.path.join(root, d))