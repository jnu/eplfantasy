# -*- coding: utf8 -*-
'''
teamdiff.py

Determine the uniqueness of a team given a control team.

---
Joe Nudell, 2013
'''

# local
import eplstats
import optimize_roster as optr
# 3rd party
import numpy as np
# stdlib
import os
import re
import codecs
import argparse
from sys import stderr, exit



def _get_line_slices(formatstr):
    '''Get the fixed-width line break points from a format string'''
    ms = re.findall(r'\{.+?(\d+?)\}', formatstr)

    return [int(b) for b in ms]


def _slice_line(line, points):
    '''Slice a line into the pieces as specified by break points in `points`'''
    slices = []

    i = 0
    for point in points:
        slices.append(line[i:i+point].strip())
        i += point

    return slices


def read_team_file(fh):
    '''Read the team roster from the given file object. Should be in the
    format that is outputted by optimize_roster.'''
    keys = []
    roster = []
    slice_points = _get_line_slices(optr.roster_line_format)

    for i, line in enumerate(fh.readlines()):
        if i == 0 :
            # Header row: read as keys
            keys = _slice_line(line, slice_points)

            # Make header names easier to work with
            keys = [re.sub(r'\s+', '_', k.lower()) for k in keys]
            continue

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



def team_similarity(roster1, roster2, players, freqfield='ownership'):
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
        in_team_one = optr.player_in_roster(player, roster1) is not None
        in_team_two = optr.player_in_roster(player, roster2) is not None

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
    cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    return cos





def get_player_stats(source, username=None, password=None):
    '''Execute downloading of all player stats from provided source.'''
    positions = ['forwards', 'midfielders', 'defenders', 'keepers']

    downloader = eplstats.Downloader(source=source,
        username=username, password=password)

    all_players = []

    for position in positions:
        print >>stderr, "  Getting stats about %s ..." % position
        _partial_players = downloader.get(position,
            source=source, season=season, adjustments=None)

        all_players += _partial_players

    return all_players






if __name__=='__main__':
    '''Find the uniqueness of two teams.'''

    # defaults
    season = 2014
    username = ''
    password = ''
    source = 'espn'

    parser = argparse.ArgumentParser(description=__doc__)

    # Required positionals:
    parser.add_argument('path_to_team1', type=str, nargs=1,
        help="Path to a team roster")
    parser.add_argument('path_to_team2', type=str, nargs=1,
        help="Path to another team roster")

    # Optional arguments
    parser.add_argument('-y', '--season', type=int, default=season,
        help="ESPN endpoint only currently supports 2014 season")
    parser.add_argument('-u', '--username', type=str, default=username,
        help="Username (for official EPL site)")
    parser.add_argument('-p', '--password', type=str, default=password,
        help="Password (for official EPL site)")
    parser.add_argument('-w', '--source', type=str, default=source,
        help="Stats source website. ESPN and EPL are supported.")

    cli = parser.parse_args()

    fn1 = cli.path_to_team1[0]
    fn2 = cli.path_to_team2[0]

    # Make sure paths to files provided exist
    for fn in [fn1, fn2]:
        if not os.path.exists(fn):
            raise IOError("Can't find %s" % fn)


    # Run stats downloader
    print >>stderr, "Fetching stats from %s ..." % cli.source
    players = get_player_stats(cli.source,
        username=cli.username, password=cli.password)
    print >>stderr, "Done."

    # Get team rosters
    print >>stderr, "Processing team files ...",
    with codecs.open(fn1, 'r', 'utf8') as fh:
        roster1 = read_team_file(fh)

    with codecs.open(fn2, 'r', 'utf8') as fh:
        roster2 = read_team_file(fh)

    print >>stderr, "done."


    # Calculate similarity
    print >>stderr, "Calculating similarity ...",
    similarity = team_similarity(roster1, roster2, players)
    print >>stderr, "done."


    # Display result
    print
    print "Team similarity:", similarity
    print




