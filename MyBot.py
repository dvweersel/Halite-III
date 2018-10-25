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

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("MyPythonBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

HALITE_RETURN_VALUE = 500

""" <<<Game Loop>>> """
while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    me_ships = me.get_ships_id()
    logging.info('We have {} ships'.format(len(me_ships)))

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []

    for ship in me.get_ships():
        logging.info(ship)

        # Featurelist
        # - Total cost of path to (nearest) dropoff?
        # - halite amount
        # - Neighbouring halite amount
        # - Cutoff value?
        #


        if ship.halite_amount > HALITE_RETURN_VALUE:
            ship.objective = constants.OBJECTIVE_RETURN

        if ship.objective == constants.OBJECTIVE_RETURN:
            if game_map.calculate_distance(ship.position, me.shipyard.position) == 0:
                logging.info("=BACK TO MINING")
                ship.objective = constants.OBJECTIVE_MINE
            else:
                logging.info("=Returning")
                command_queue.append(
                    ship.move(
                        game_map.naive_navigate(ship, me.shipyard.position)))
        elif ship.objective == constants.OBJECTIVE_MINE:
            # For each of your ships, move randomly if the ship is on a low halite location or the ship is full.
            #   Else, collect halite.
            if ship.halite_amount < game_map[ship.position].halite_amount/constants.MOVE_COST_RATIO:
                logging.info('=Not enough halite to move')
                command_queue.append(ship.stay_still())

            elif game_map[ship.position].halite_amount < constants.MAX_HALITE / 10:
                logging.info('=Looking for mining spots')

                neighbours = ship.position.get_surrounding_cardinals()
                directions = Direction.get_all_cardinals()
                neighbours_halite = [game_map[pos].halite_amount if not(game_map[pos].is_occupied) else -1 for pos in neighbours]
                max_index = np.argmax(neighbours_halite)
                move = directions[max_index]

                command_queue.append(
                    ship.move(move))
                game_map[neighbours[max_index]].mark_unsafe(ship)

            else:
                logging.info('=Mining')
                command_queue.append(ship.stay_still())

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

