#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction

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
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("MyBot-v11")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

TIMING = False

HALITE_RETURN_VALUE = 800
mission_control = {}

""" <<<Game Loop>>> """
while True:
    if TIMING: round_timer_start = timer()
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    me_ships = me.get_ships_id()
    logging.info('We have {} ships'.format(len(me_ships)))

    if TIMING: map_timer_start = timer()
    if game.turn_number == 1:
        distance_map, initial_halite = game_map.dijkstra_map(me.shipyard)
        avg_halite = initial_halite
        halite_collected = 0
        logging.info("Inital halite is: {}".format(initial_halite))
    else:
        distance_map, avg_halite = game_map.dijkstra_map(me.shipyard)
        halite_collected = 1 - avg_halite / initial_halite
        logging.info("Average halite is: {}, {}".format(avg_halite, halite_collected))


    if TIMING: map_timer_end = timer()
    if TIMING: logging.info("Created map in {}".format(map_timer_end-map_timer_start))

    remaining_turns = constants.MAX_TURNS - game.turn_number
    suicide = False
    if remaining_turns < 25:
        suicide = True
    # SET THE OBJECTIVE
    logging.info("SETTING OBJECTIVES")
    for ship in me.get_ships():
        # Returning
        ship_id = ship.id
        logging.info(ship)
        logging.info("Objective: {}".format(mission_control.get(ship_id)))
        if suicide:
            mission_control[ship.id] = constants.OBJECTIVE_SUICIDE
            logging.info("Mizu no yo ni nagare")
        elif mission_control.get(ship_id) == constants.OBJECTIVE_RETURN:
            if ship.position == me.shipyard.position:
                # We have reached the dropoff; Mining
                logging.info("=DROPOFF SUCCESFUL")
                mission_control[ship.id] = constants.OBJECTIVE_MINE
            else:
                # Returning
                logging.info("=RETURNING")
                mission_control[ship.id] = constants.OBJECTIVE_RETURN
        elif mission_control.get(ship_id) == constants.OBJECTIVE_MINE:
            if ship.halite_amount > HALITE_RETURN_VALUE:
                logging.info("=RETURNING")
                mission_control[ship.id] = constants.OBJECTIVE_RETURN
        else:
            mission_control[ship.id] = constants.OBJECTIVE_MINE

        logging.info("New objective: {}".format(mission_control.get(ship_id)))

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_list = OrderedDict({})
    for ship in me.get_ships():
        logging.info("={}".format(ship))
        objective = mission_control.get(ship.id)
        logging.info("Objective: {}".format(objective))
        # MOVE ACCORDING TO OBJECTIVE
        # DYING
        if objective == constants.OBJECTIVE_SUICIDE:
            logging.info('Brb, killing myself')
            target_direction = game_map.navigate_back(ship, distance_map)

        # RETURNING
        if objective == constants.OBJECTIVE_RETURN:
            if ship.halite_amount < game_map[ship.position].halite_amount/constants.MOVE_COST_RATIO:
                logging.info('Not enough halite to move. Going back to mining')
                mission_control[ship.id] = constants.OBJECTIVE_MINE
            else:
                logging.info("Returning")
                target_direction = game_map.navigate_back(ship, distance_map)

        # Mining
        if objective == constants.OBJECTIVE_MINE:
            # For each of your ships, move towards the highest neighbouring halite
            if ship.halite_amount < game_map[ship.position].halite_amount / constants.MOVE_COST_RATIO:
                logging.info('Not enough halite to move')
                target_direction = Direction.Still
                mission_control[ship.id] = constants.OBJECTIVE_MINE

            elif game_map[ship.position].halite_amount < avg_halite/15 and game_map[ship.position].halite_amount < 100:

                neighbours = ship.position.get_surrounding_cardinals()
                neighbours_halite = [game_map[pos].halite_amount if not (game_map[pos].is_occupied) else -1 for pos in
                                     neighbours]

                if any(x > avg_halite/8 for x in neighbours_halite):
                    logging.info('Mining neighbour')
                    target_direction = game_map.mining(ship)
                else:
                    logging.info('Looking for mining spots')
                    target_direction = game_map.finding_halite(ship)

            # We are at an optimal spot. Mine
            else:
                logging.info('Mining')
                target_direction = Direction.Still

        # Store move information
        ship_destination = game_map.normalize(ship.position.directional_offset(target_direction))
        command_list.update({ship.id: [ship_destination, target_direction]})

    destination_list = Counter([dest for dest, dir in command_list.values()])
    logging.info("Dest list: {}".format(destination_list))

    logging.info("Sum: {}, Length: {}".format(sum(destination_list.values()),len(destination_list)))

    while sum(destination_list.values()) != len(destination_list):
        item = command_list.popitem()

        logging.info("Popping {}".format(item))
        logging.info("Command list: {}".format(command_list))
        id = item[0]
        destination = item[1][0]
        direction = item[1][1]

        ship = me.get_ship(id)

        if destination_list[destination] > 1 and direction != Direction.Still:
            command_list.update({id: [ship.position, Direction.Still]})
        else:
            command_list.update({id: [destination, direction]})

        command_list.move_to_end(id, False)
        logging.info("Collisions: {}".format(sum(destination_list.values()) - len(destination_list)))
        destination_list = Counter([dest for dest, dir in command_list.values()])
        if suicide:
            del destination_list[me.shipyard.position]
        logging.info("Dest list: {}".format(destination_list))

    # Avoid getting stuck
    near_spawn = [game_map[x].ship for x in me.shipyard.position.get_surrounding_cardinals() if game_map[x].ship != None]
    if len(near_spawn) == 4 and game_map[me.shipyard.position].ship != None and game_map[me.shipyard.position].ship.owner == me.id:

        deadlock = all(mission_control[blocker.id] == constants.OBJECTIVE_RETURN for blocker in near_spawn if blocker.owner == me.id)
        if deadlock:
            deadman = game_map[me.shipyard.position].ship
            command_list.update({deadman.id: ["Fucked", Direction.North]})

    logging.info("Collisions: {}".format(sum(destination_list.values()) - len(destination_list)))
    logging.info("Command list: {}".format(command_list))

    # Make the moves
    command_queue = []
    for id, array in command_list.items():
        ship = me.get_ship(id)
        direction = array[1]
        command_queue.append(ship.move(direction))

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    ship_at_port = any(pos == me.shipyard.position for pos in destination_list.keys())
    if halite_collected < 1/amount_of_players and me.halite_amount >= constants.SHIP_COST and not ship_at_port:
        if game.turn_number <= constants.MAX_TURNS/2:
            command_queue.append(me.shipyard.spawn())
    else:
        HALITE_RETURN_VALUE = 900

    if TIMING: round_timer_end = timer()
    if TIMING: logging.info("Round took {} second".format(round_timer_end - round_timer_start))
    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)