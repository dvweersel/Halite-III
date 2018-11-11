import queue

from . import constants
from .entity import Entity, Shipyard, Ship, Dropoff
from .player import Player
from .positionals import Direction, Position
from .common import read_input
import logging

from math import inf
import numpy as np

from timeit import default_timer as timer

from heapq import *

class MapCell:
    """A cell on the game map."""
    def __init__(self, position, halite_amount):
        self.position = position
        self.halite_amount = halite_amount
        self.ship = None
        self.structure = None
        self.potential = 0

    @property
    def is_empty(self):
        """
        :return: Whether this cell has no ships or structures
        """
        return self.ship is None and self.structure is None

    @property
    def is_occupied(self):
        """
        :return: Whether this cell has any ships
        """
        return self.ship is not None

    @property
    def has_structure(self):
        """
        :return: Whether this cell has any structures
        """
        return self.structure is not None

    @property
    def structure_type(self):
        """
        :return: What is the structure type in this cell
        """
        return None if not self.structure else type(self.structure)

    def mark_unsafe(self, ship):
        """
        Mark this cell as unsafe (occupied) for navigation.

        Use in conjunction with GameMap.naive_navigate.
        """
        self.ship = ship

    def __eq__(self, other):
        return self.position == other.position

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'MapCell({}, halite={})'.format(self.position, self.halite_amount)

class GameMap:
    """
    The game map.

    Can be indexed by a position, or by a contained entity.
    Coordinates start at 0. Coordinates are normalized for you
    """
    def __init__(self, cells, width, height):
        self.width = width
        self.height = height
        self._cells = cells

    def __getitem__(self, location):
        """
        Getter for position object or entity objects within the game map
        :param location: the position or entity to access in this map
        :return: the contents housing that cell or entity
        """
        if isinstance(location, Position):
            location = self.normalize(location)
            return self._cells[location.y][location.x]
        elif isinstance(location, Entity):
            return self._cells[location.position.y][location.position.x]
        return None

    def calculate_distance(self, source, target):
        """
        Compute the Manhattan distance between two locations.
        Accounts for wrap-around.
        :param source: The source from where to calculate
        :param target: The target to where calculate
        :return: The distance between these items
        """
        source = self.normalize(source)
        target = self.normalize(target)
        resulting_position = abs(source - target)
        return min(resulting_position.x, self.width - resulting_position.x) + \
            min(resulting_position.y, self.height - resulting_position.y)

    def normalize(self, position):
        """
        Normalized the position within the bounds of the toroidal map.
        i.e.: Takes a point which may or may not be within width and
        height bounds, and places it within those bounds considering
        wraparound.
        :param position: A position object.
        :return: A normalized position object fitting within the bounds of the map
        """
        return Position(position.x % self.width, position.y % self.height)

    @staticmethod
    def _get_target_direction(source, target):
        """
        Returns where in the cardinality spectrum the target is from source. e.g.: North, East; South, West; etc.
        NOTE: Ignores toroid
        :param source: The source position
        :param target: The target position
        :return: A tuple containing the target Direction. A tuple item (or both) could be None if within same coords
        """
        return (Direction.South if target.y > source.y else Direction.North if target.y < source.y else None,
                Direction.East if target.x > source.x else Direction.West if target.x < source.x else None)

    def get_unsafe_moves(self, source, destination):
        """
        Return the Direction(s) to move closer to the target point, or empty if the points are the same.
        This move mechanic does not account for collisions. The multiple directions are if both directional movements
        are viable.
        :param source: The starting position
        :param destination: The destination towards which you wish to move your object.
        :return: A list of valid (closest) Directions towards your target.
        """
        source = self.normalize(source)
        destination = self.normalize(destination)
        possible_moves = []
        distance = abs(destination - source)
        y_cardinality, x_cardinality = self._get_target_direction(source, destination)

        if distance.x != 0:
            possible_moves.append(x_cardinality if distance.x < (self.width / 2)
                                  else Direction.invert(x_cardinality))
        if distance.y != 0:
            possible_moves.append(y_cardinality if distance.y < (self.height / 2)
                                  else Direction.invert(y_cardinality))
        return possible_moves

    def mining(self, ship):
        neighbours = ship.position.get_surrounding_cardinals()
        directions = Direction.get_all_cardinals()
        neighbours_halite = [self[pos].halite_amount if not (self[pos].is_occupied) else -1 for pos in
                             neighbours]

        max_index = np.argmax(neighbours_halite)
        if self[ship.position].halite_amount == 0 \
                or neighbours_halite[max_index] > self[ship.position].halite_amount:
            move_dir = directions[max_index]
        else:
            move_dir = Direction.Still

        return move_dir

    def finding_halite(self, ship, id):

        normalize = self.normalize
        calculate_potential = self._calculate_potential_cell

        logging.info("Calculating best potential for {}".format(ship.position))
        potential_highest = 0
        move_dir = Direction.Still

        for direction in Direction.get_all_cardinals():
            position = normalize(ship.position.directional_offset(direction))

            if self[position].is_occupied:
                potential = 0
            else:
                potential = calculate_potential(position, [], id)

            if potential > potential_highest:
                potential_highest = potential
                move_dir = direction

        return move_dir

    def _calculate_potential_cell(self, source, dropoffs, id):
        """
        Calculates the potential of a point
        :param: The position for which te calculate dropoffs
        :param: A list of the dropoffs
        :return: the potential:
        """
        normalize = self.normalize

        q, seen = [], {}

        range = self.width+self.height
        potential = 0

        heappush(q, (0, source))
        while q:
            (distance, position) = heappop(q)

            if position in seen:
                continue

            # Add to seen
            seen[position] = distance

            if self[position].ship is None:
                # Calculate potential
                halite_cell = self[position].halite_amount
                structure_cell = self[position].structure

                range_factor = (range - distance)
                if structure_cell is not None and structure_cell.id == id:
                    potential += -1000*range_factor
                else:
                    potential += halite_cell*range_factor*range_factor

                # Add new nodes
                new_distance = distance + 1
                for neighbour in position.get_surrounding_cardinals():
                    heappush(q, (new_distance, normalize(neighbour)))

        logging.info("Potential of {} is {}".format(source, potential))

        return potential

    def dijkstra_map(self, base):
        """
        Creates a dijkstra map containing cost of returning to the shipyard
        :return: The shipyard:
        """
        normalize = self.normalize

        q, cost_map = [], {}

        avg_halite = 0
        heappush(q, (0, base.position))
        while q:
            (cost, position) = heappop(q)

            if position in cost_map:
                continue

            avg_halite += self[position].halite_amount

            cost_map[position] = cost

            for neighbour in position.get_surrounding_cardinals():
                neighbour = normalize(neighbour)
                avg_halite += self[neighbour].halite_amount
                new_cost = cost + self[neighbour].halite_amount/10 + 50
                heappush(q, (new_cost, neighbour))

        avg_halite = avg_halite/(self.width*self.height)
        return cost_map, avg_halite

    def navigate_back(self, ship, dijkstra_map):
        """
        Returns a direction following the dijkstra_map
        :return: The direction:
        """
        cost = dijkstra_map[ship.position]
        move_dir = Direction.Still

        for direction in Direction.get_all_cardinals():
            target_pos = self.normalize(ship.position.directional_offset(direction))
            if dijkstra_map[target_pos] < cost:
                cost = dijkstra_map[target_pos]
                move_dir = direction

        return move_dir

    @staticmethod
    def _generate():
        """
        Creates a map object from the input given by the game engine
        :return: The map object
        """
        map_width, map_height = map(int, read_input().split())
        game_map = [[None for _ in range(map_width)] for _ in range(map_height)]
        for y_position in range(map_height):
            cells = read_input().split()
            for x_position in range(map_width):
                game_map[y_position][x_position] = MapCell(Position(x_position, y_position),
                                                           int(cells[x_position]))
        return GameMap(game_map, map_width, map_height)

    def _update(self):
        """
        Updates this map object from the input given by the game engine
        :return: nothing
        """
        # Mark cells as safe for navigation (will re-mark unsafe cells
        # later)
        for y in range(self.height):
            for x in range(self.width):
                self[Position(x, y)].ship = None

        for _ in range(int(read_input())):
            cell_x, cell_y, cell_energy = map(int, read_input().split())
            self[Position(cell_x, cell_y)].halite_amount = cell_energy
