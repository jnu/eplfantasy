'''
optimize_roster.py 

Optimize a fantasy English Premier List roster.

---
Fetches stats from ESPN EPL fantasy server and parses them via eplstats.py.
Then search for a solution to the Knapsack Problem that is constrained by
the number of players (and in the right positions) and also the given budget.

The optimization may take a while to happen, and as it is NP-Complete it does
not always produced a guaranteed optimal solution.

The output of the program will be status information and graphs while the
search is on-going, but will ultimately result in a suggested team roster.

The team roster will contain 15 players:
2 keepers, 5 defenders, 5 midfielders, and 3 forwards.

Currently the output does NOT suggest what formation to play these players
in, nor does it tell you who should start and who should sub. These are
coming features.

---
Joe Nudell
'''

from openopt import *
from pprint import pprint
from sys import stderr, exit
import eplstats
import argparse


def get_player_stats(season=2014, benchfrac=.1):
    '''Get all the stats from ESPN.com and format them in the manner
    expected by the optimizer.'''
    players = []

    _positions = ['forwards', 'midfielders', 'defenders', 'keepers']

    for position in _positions:
        _players = eplstats.get(position, season=season)

        for player in _players:
            for captain in [0, 1]:
                for pfx in ['', 'sub-']:

                    # Create a postfix for the name including semantic details
                    # about the given options
                    postfix = "starter" if not len(pfx) else "sub"
                    postfix += "- captain" if captain else ""

                    points = player.average_points
                    if len(pfx)>0:
                        # Severely down-weight scores of benched players
                        points *= benchfrac

                    if captain:
                        # Captains earn double points
                        points *= 2.

                    stats = {
                        'cost' : player.cost,
                        'score' : points,
                        'name' : ("%s %s - %s - %s" % \
                            (
                                player.first_name,
                                player.last_name,
                                position[:-1],
                                postfix
                            )).strip(),
                        'captain' : captain,
                        'keeper' : 0,
                        'defender' : 0,
                        'midfielder' : 0,
                        'forward' : 0,
                        'sub-keeper' : 0,
                        'sub-defender' : 0,
                        'sub-midfielder' : 0,
                        'sub-forward' : 0
                    }

                    # Set the field for current position played by player
                    stats[pfx+position[:-1]] = 1

                    players.append(stats)

    return players



if __name__=='__main__':
    # Defaults
    season = 2014
    tolerance = .05
    budget = 100.
    bench = 1/26.

    # Get CL params
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('-s', '--season', type=int, default=season,
        help="ESPN endpoint only currently supports 2014 season")
    parser.add_argument('-t', '--tolerance', type=float, default=tolerance,
        help="Fuzzy boundaries around optimal solution, default is .05")
    parser.add_argument('-b', '--budget', type=float, default=budget,
        help="Salary cap in millions of pounds, default is 100")
    parser.add_argument('-e', '--bench', type=float, default=bench,
        help="Fraction of score to reduce substitutes by, default is .1 (=1/10 of starter score")

    cli = parser.parse_args()

    # Read CLI params back into internal vars
    season = cli.season
    tolerance = cli.tolerance
    budget = cli.budget
    bench = cli.bench

    # Get stats
    print >>stderr, "Getting current stats from ESPN ...",
    players = get_player_stats(season=season, benchfrac=bench)
    print >>stderr, "done."

    # Define constraints
    constraints = lambda values : (
            values['cost'] <= budget,
            ##
            values['forward'] >= 1,
            values['forward'] <= 3,
            values['forward'] + values['sub-forward'] == 3,
            ##
            values['midfielder'] >= 3,
            values['midfielder'] <= 5,
            values['midfielder'] + values['sub-midfielder'] == 5,
            ##
            values['defender'] >= 3,
            values['defender'] <= 5,
            values['defender'] + values['sub-defender'] == 5,
            ##
            values['keeper'] == 1,
            values['sub-keeper'] == 1, 
            ##
            values['captain'] == 1,
            ##
            values['sub-forward'] + values['sub-midfielder'] \
                + values['sub-defender'] + values['sub-keeper'] == 4,
            values['nItems'] == 15 # redundant now
        )

    # Define objective: maximize score
    objective = [
        'score', tolerance, 'max'
    ]

    # Construct problem
    p = KSP(objective, players, constraints=constraints, name='ksp_mop')

    # Run optimizer
    r = p.solve('glpk', plot=1, iprint=1, nProc=2)


    # Output solution
    print >>stderr, "Best solution found:"
    pprint(r.xf)