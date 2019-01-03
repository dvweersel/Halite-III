#!/usr/bin/env pypy
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position


# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

# My imports
import numpy as np
from collections import Counter, OrderedDict
from timeit import default_timer as timer

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()

amount_of_players = len(game.players)

# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.graph =

distance_map, initial_halite = game.game_map.dijkstra_map(game.me.shipyard)
logging.info("Inital halite is: {}".format(initial_halite))

game.ready("MyPythonBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

STOP_VALUE_COLLECTING = 0.55

# Game states: 'early', 'mid'
game_state = constants.GAME_STATE_EARLY

# Mission control is a dict, where an objective is assigned for each ship.
mission_control = {}
""" <<<Game Loop>>> """
while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()

    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # These are my ships
    me_ships = me.get_ships()
    logging.info('We have {} ships'.format(len(me_ships)))

    distance_map, avg_halite = game_map.dijkstra_map(me.shipyard)
    halite_collected = 1 - avg_halite / initial_halite
    logging.info("Halite distribution: avg: {}, collected {}".format(avg_halite, halite_collected))

    remaining_turns = constants.MAX_TURNS - game.turn_number

    # Determine gamestate
    if avg_halite < STOP_VALUE_COLLECTING:
        game_state = constants.GAME_STATE_EARLY

    # SET THE OBJECTIVE
    logging.info("SETTING OBJECTIVES")
    calculate_distance = game_map.calculate_distance

    # if game_map.is_depleted(me.shipyard, avg_halite/8) and not(creating_dropoff) and remaining_turns > 100:
    #     creating_dropoff = True
    #
    #     ship_id, highest_potential = 0, 0
    #     for ship in me.get_ships():
    #         potential = game_map.calculate_potential_cell(ship.position)
    #         if potential > highest_potential:
    #             ship_id = ship.id
    #             highest_potential = potential
    #
    #     mission_control[ship_id] = constants.OBJECTIVE_DROPOFF

    # The command list holds the commands for  this turn
    command_list = OrderedDict({})
    destination_list = []
    for ship in me_ships:
        ship_id = ship.id
        logging.info(ship)
        logging.info("Objective: {}".format(mission_control.get(ship_id)))

        distance_to_shipyard = calculate_distance(ship.position, me.shipyard.position)

        # SETTING OBJECTIVE
        if mission_control.get(ship_id) == constants.OBJECTIVE_SUICIDE or distance_to_shipyard+10 > remaining_turns:
            mission_control[ship.id] = constants.OBJECTIVE_SUICIDE
            logging.info("Mizu no yo ni nagare")
            mission_control[ship.id] = constants.OBJECTIVE_SUICIDE
        elif mission_control.get(ship_id) == constants.OBJECTIVE_RETURN:
            if ship.position == me.shipyard.position:
                logging.info("Dropped cargo, mining")
                mission_control[ship.id] = constants.OBJECTIVE_MINE
            else:
                logging.info("Returning")
                mission_control[ship.id] = constants.OBJECTIVE_RETURN
        elif mission_control.get(ship_id) == constants.OBJECTIVE_MINE:
            if ship.halite_amount > 0.9*constants.MAX_HALITE:
                logging.info("We are full. Returning")
                mission_control[ship.id] = constants.OBJECTIVE_RETURN
        else:
            logging.info("Dunno. Mine I guess")
            mission_control[ship.id] = constants.OBJECTIVE_MINE

        objective = mission_control.get(ship.id)
        logging.info("Objective: {}".format(objective))

        # MOVE ACCORDING TO OBJECTIVE
        # CANT MOVE
        if ship.halite_amount < game_map[ship.position].halite_amount / constants.MOVE_COST_RATIO:
            logging.info("Not enough halite to move")
            target_direction = Direction.Still
        # SUICIDE
        elif objective == constants.OBJECTIVE_SUICIDE:
            logging.info('Brb, killing myself')
            cost = distance_map[ship.position]
            target_direction = Direction.Still

            for direction in game_map.get_unsafe_moves(ship.position, me.shipyard.position):
                target_pos = game_map.normalize(ship.position.directional_offset(direction))
                if target_pos == me.shipyard.position:
                    target_direction = direction
                elif distance_map[target_pos] < cost and target_pos not in destination_list:
                    cost = distance_map[target_pos] + 50
                    target_direction = direction

        # RETURNING
        elif objective == constants.OBJECTIVE_RETURN:
            logging.info("Returning")
            target_direction = game_map.navigate_back(ship, distance_map)
        # MINING
        elif objective == constants.OBJECTIVE_MINE:

            if game_map[ship.position].halite_amount < avg_halite / 15 or game_map[ship.position].halite_amount < 50:

                neighbours = ship.position.get_surrounding_cardinals()
                neighbours_halite = [game_map[pos].halite_amount if not (game_map[pos].is_occupied) else -1 for pos in
                                     neighbours]

                if any(x > avg_halite / 8 for x in neighbours_halite):
                    logging.info('Mining neighbour')
                    target_direction = game_map.mining(ship)
                else:
                    logging.info('Looking for mining spots')
                    target_direction = game_map.finding_halite(ship, me.id)

            # We are at an optimal spot. Mine
            else:
                logging.info('Mining')
                target_direction = Direction.Still

        # STORE MOVES
        ship_destination = game_map.normalize(ship.position.directional_offset(target_direction))
        destination_list.append(ship_destination)
        command_list.update({ship.id: [ship_destination, target_direction]})

    # SOLVING COLLISSIONS
    destination_list = Counter([dest for dest, dir in command_list.values()])
    while sum(destination_list.values()) != len(destination_list):
        item = command_list.popitem()

        id = item[0]
        destination = item[1][0]
        direction = item[1][1]

        ship = me.get_ship(id)

        if destination_list[destination] > 1 and direction != Direction.Still:
            command_list.update({id: [ship.position, Direction.Still]})
        else:
            command_list.update({id: [destination, direction]})

        command_list.move_to_end(id, False)
        # logging.info("Collisions: {}".format(sum(destination_list.values()) - len(destination_list)))
        destination_list = Counter([dest for dest, dir in command_list.values()])
        if constants.OBJECTIVE_SUICIDE in mission_control.values():
            del destination_list[me.shipyard.position]
        # logging.info("Dest list: {}".format(destination_list))

    # AVOID DEADLOCK
    near_spawn = [game_map[x].ship for x in me.shipyard.position.get_surrounding_cardinals() if game_map[x].ship != None]
    if len(near_spawn) == 4 and game_map[me.shipyard.position].ship != None and game_map[me.shipyard.position].ship.owner == me.id:

        deadlock = all(mission_control[blocker.id] == constants.OBJECTIVE_RETURN for blocker in near_spawn if blocker.owner == me.id)
        if deadlock:
            deadman = game_map[me.shipyard.position].ship
            command_list.update({deadman.id: ["Fucked", Direction.North]})

    # logging.info("Collisions: {}".format(sum(destination_list.values()) - len(destination_list)))
    logging.info("Command list: {}".format(command_list))

    # FILL UP COMMAND QUEU
    command_queue = []
    for id, array in command_list.items():
        ship = me.get_ship(id)
        direction = array[1]
        command_queue.append(ship.move(direction))

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    ship_at_port = any(pos == me.shipyard.position for pos in destination_list.keys())
    if game_state == constants.GAME_STATE_EARLY and me.halite_amount >= constants.SHIP_COST and not ship_at_port:
        if game.turn_number <= constants.MAX_TURNS/2:
            command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
