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
import os
import re


def get_player_stats(season=2014, benchfrac=.1):
    '''Get all the stats from ESPN.com and format them in the manner
    expected by the optimizer.'''
    players = []

    _positions = ['forwards', 'midfielders', 'defenders', 'keepers']
    _id = 0
    _uid = 990000

    for position in _positions:
        _players = eplstats.get(position, season=season)

        for player in _players:
            _id += 1

            for captain in [0, 1]:
                for pfx in ['', 'sub-']:
                    _uid += 1

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
                        'pid' : _id,
                        'uid' : _uid,
                        'bench' : "starter" if not len(pfx) else "sub",
                        'position' : position[:-1],
                        'fname' : player.first_name,
                        'lname' : player.last_name,
                        'club' : player.club,
                        'name' : ("%s %s - %s - %s (%d)" % \
                            (
                                player.first_name,
                                player.last_name,
                                position[:-1],
                                postfix,
                                _uid
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

    all_ids = range(_id + 1)
    for player in players:
        for i in all_ids:
            player['id%d' % i] = float(player['pid']==i)


    return players



if __name__=='__main__':
    # Defaults
    season = 2014
    tolerance = 10**-6
    budget = 100.
    bench = 1/10.

    # Get CL params
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('-s', '--season', type=int, default=season,
        help="ESPN endpoint only currently supports 2014 season")
    parser.add_argument('-t', '--tolerance', type=float, default=tolerance,
        help="Fuzzy boundaries around optimal solution, default is 10e-6")
    parser.add_argument('-b', '--budget', type=float, default=budget,
        help="Salary cap in millions of pounds, default is 100")
    parser.add_argument('-e', '--bench', type=float, default=bench,
        help="Fraction of score to reduce substitutes by, default is 1/10")

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
    print >>stderr, "Defining constraints ...",
    all_ids = range(players[-1]['pid']+1)
    
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
            ##
            #values['nItems'] == 15 # redundant now
        )+tuple([values['id%d'%i]<=1 for i in all_ids])

    print >>stderr,"done."


    # Define objective: maximize score
    objective = [
        'score', tolerance, 'max'
    ]


    print >>stderr, "Solving problem ..."

    # Construct problem
    p = KSP(objective, players, constraints=constraints, name='ksp_mop')

    # Run optimizer
    r = p.solve('glpk', iprint=1, nProc=2)


    # Output solution
    print >>stderr, "Best solution found:"
    pprint(r.xf)


    os.system('clear')
    names = r.xf

    # Find selected players in `players` list
    uids = []
    for name in names:
        # Get unique id from name
        m = re.search(r'\((\d+)\)', name)
        if m is None:
            raise ValueError("Can't find UID in %s" % name)

        uid = int(m.group(1))

        uids.append(uid)

    roster = []
    for player in players:
        if player['uid'] in uids:
            roster.append(player)

    # Print details about selected roster
    row_format= "{:<15}{:<15}{:<15}{:<14}{:<6}{:<5}{:<7}"

    print row_format.format('First Name',
        'Last Name', 'Position', 'Starting', 'Capt.', 'Club', 'Salary')

    total_cost = 0.
    for player in roster:
        total_cost += player['cost']
        print row_format.format(player['fname'],
            player['lname'], player['position'], player['bench'],
            "X" if player['captain'] else "",
            player['club'], player['cost'])

    print 
    print "Total Cost:\t", total_cost, "M"
    print "Under budget:\t", budget-total_cost, "M"
    print






