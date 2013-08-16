# -*- coding: utf8 -*-
'''
teamdiff.py

Determine the uniqueness of a team given a control team.

---
Joe Nudell, 2013
'''

# local
import eplstats
from optimize_roster import get_player_stats, roster_line_format
# 3rd party
import numpy as np
# stdlib
import os
import re
from sys import stderr, exit



def _get_line_slices(formatstr):
    '''Get the fixed-width line break points from a format string'''
    ms = re.findall(r'\{.+\d+?\}', formatstr)

    return [int(b) for b in ms]


def _slice_line(line, points):
    '''Slice a line into the pieces as specified by break points in `points`'''
    slices = []

    i = 0
    for point in points:
        slices.append(line[i:point].strip())
        i += point

    return slices


def read_team_file(fh):
    '''Read the team roster from the given file object. Should be in the
    format that is outputted by optimize_roster.'''
    keys = []
    roster = []
    slice_points = _get_line_slices(roster_line_format)

    for i, line in enumerate(fh.readlines())
        if i == 0 :
            # Header row: read as keys
            keys = _slice_line(line, slice_points)
        elif i == 1:
            # These are just delimeters
            continue
        else:
            # Interpret content line
            slices = _slice_line(line, slice_points)

            # Adjust types
            slices[-1] = float(slices[-1])
            slices[-3] = len(slices[-3])>0

            # Make dict using keys from header
            new_player = dict(zip(keys, slices))

            roster.append(new_player)

    return roster


def find_player_in_roster(player, roster):
    '''Check whether player is in roster. Difficult problem because of name
    variations used in roster, but match is attempted anyway with several
    heuristics.'''
    


def team_similarity(roster1, roster1, players, freqfield='popularity'):
    '''Compare the rosters of two teams using statistics provided in the list
    `players`. Comparison is cosine similarity of TF-IDF vectors created from
    these rosters. Return value is in [0, 1]. A value of 1 means that the 
    teams are identical. A value of 0 means that teams share no players in
    common.'''

    v1 = np.zeros(len(players))
    v2 = np.zeros(len(players))

    for i, player in enumerate(players):
        # Calculate inverse frequency of player selection for all players
        # selected in both teams. Same idea as TF-IDF in document similarity.
        in_team_one = find_player_in_roster(player, roster1)
        in_team_two = find_player_in_roster(player, roster2)

        if not in_team_one and not in_team_two:
            continue

        freq = float(getattr(player, freqfield))

        ipf = np.log(1./freq)

        if in_team_one:
            v1[i] = ipf

        if in_team_two:
            v2[i] = ipf

    # TODO - verify that there are 15 elements in both teams?

    # Calculate cos(θ) between vectors
    cos = np.linalg.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    return cos



