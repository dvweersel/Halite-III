#!/usr/bin/env python3
import os
import numpy as np
import json

import os
import shutil

rounds = 10

tracker = np.array([0,0])

for i in range(rounds):
    print("Match: {}".format(i))
    os.system('call activate halite')
    os.system('halite.exe --replay-directory replays/ -vvv --width 32 --height 32 --results-as-json "python MyBot.py" "python MyOldBot.py" >> data.gameout')
    os.system('call deactivate')

    with open('data.gameout', 'r') as f:
        output = json.load(open("data.gameout"))


        players = [player_stats for player_stats in output['stats']]

        stats = [output['stats'][player_id]['rank'] for player_id in players]
        halite = [output['stats'][player_id]['score'] for player_id in players]
        wins = [1 if x == 1 else 0 for x in stats]

        tracker = np.add(tracker, wins)

        bot1_rank = output['stats']['0']['rank']
        bot1_halite = output['stats']['0']['score']

        bot2_rank = output['stats']['1']['rank']
        bot2_halite = output['stats']['1']['score']

        # print("bot1 rank: {} halite: {}".format(stats[0], halite[0]))
        # print("bot2 rank: {} halite: {}".format(stats[1], halite[1]))

    os.remove('data.gameout')

print("bot1 won {}%".format(tracker[0]/rounds*100))
print("bot2 won {}%".format(tracker[1]/rounds*100))

for root, dirs, files in os.walk('./replays/'):
    for f in files:
        os.unlink(os.path.join(root, f))
    for d in dirs:
        shutil.rmtree(os.path.join(root, d))