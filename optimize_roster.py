# -*-coding: utf8-*-
'''
optimize_roster.py 

Optimize a fantasy English Premier List roster.

---
Fetches stats from ESPN EPL fantasy server and parses them via eplstats.py.
Then search for a solution to the Knapsack Problem that is constrained by
the number of players (and in the right positions) and also the given budget.

The optimization may take a while to happen, and as it is NP-Complete it does
not always produced a guaranteed optimal solution.

The output of the program will be status information while the search is
on-going, but will ultimately result in a suggested team roster.

The team roster will contain 15 players:
2 keepers, 5 defenders, 5 midfielders, and 3 forwards.

The algorithm will pick starters, which implicitly solves the problem of
finding the optimal formation.

The algorithm will also determine who should be captain.

A few command line arguments can be use to adjust hyperparameters related to
optimization. See them with $ python optimize_roster.py -h

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



def get_injured_list(fn, has_header=False):
    if not os.path.exists(fn):
        raise IOError("Injured list file `%s` does not exist" % fn)

    disabled_list = dict()

    with open(fn) as fh:

        for i, line in enumerate(fh.readlines()):
            if has_header and i==0:
                # Skip header line
                continue

            try:
                name, factor, notes = [t.strip() for t in t.split("  ")]
            except Exception:
                raise IOError("Injured list file `%s` is misformatted" % fn)

            try:
                factor = float(factor)
            except ValueError:
                if i==0:
                    if not has_header:
                        print >>stderr, \
                        "Warning: Header detected though has_header not set"
                    continue
                else:
                    raise ValueError("Can't parse %s as float" % factor)

            # Store player info
            disabled_list[name] = factor

    return disabled_list




def get_player_stats(score='total_points',
    season=2014, benchfrac=.1, adjustments=dict()):
    '''Get all the stats from ESPN.com and format them in the manner
    expected by the optimizer.
    Params:
     score       Can be attribute of Player or callable expecting Player as arg
     season      season to get stats for from ESPN
     benchfrac   Fraction of points awarded to substitutes
     adjustments Externally defined adjustments to player worth (injuries etc.)
    '''
    players = []

    _positions = ['forwards', 'midfielders', 'defenders', 'keepers']
    _id = 0
    _uid = 990000

    for position in _positions:
        _players = eplstats.get(position, season=season)

        for player in _players:
            _id += 1

            # Find any external adjustment factoring to player worth
            adj_id = p(layer.first_name + player.last_name).strip()
            adj_factor = 1. # default - no adjustment
            if adj_id in adjustments:
                adj_factor = adjustments[adj_id]

            for captain in [0, 1]:
                for pfx in ['', 'sub-']:
                    _uid += 1

                    # Create a postfix for the name including semantic details
                    # about the given options
                    postfix = "starter" if not len(pfx) else "sub"
                    postfix += "- captain" if captain else ""

                    # Get score from. Default is to pass string for attribute
                    # on Player instance, but can do a lambda or other
                    # callable as well.
                    points = 0.
                    if hasattr(score, '__call__'):
                        points = score(player)
                    else:
                        points = getattr(player, score)

                    if len(pfx)>0:
                        # Severely down-weight scores of benched players
                        points *= benchfrac

                    if captain:
                        # Captains earn double points
                        points *= 2.

                    # Factor in external adjustments (default is just 1.0)
                    points *= adj_factor

                    # Build player instance for insertion into talent pool
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

    # Create player id fields to build uniqueness constraints
    all_ids = range(_id + 1)
    for player in players:
        for i in all_ids:
            player['id%d' % i] = float(player['pid']==i)

    return players





def optimize(season=2014,
    tolerance=1e-6, budget=100., bench=.1,
    adjustments=None, score="total_points", solver="glpk"):
    '''Configure and run KSP solver with given parameters. Returns openopt's
    solution object'''

    # Get adjustments, if a file is given
    adj_file = adjustments
    if adj_file is not None:
        adjustments = get_injured_list(adj_file)

    # Get stats
    print >>stderr, "Getting current stats from ESPN ...",
    players = get_player_stats(season=season,
        benchfrac=bench, score=score, adjustments=adjustments)
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
            # And now add uniqueness constraints: all pids must be unique
        ) + tuple([values['id%d'%i]<=1 for i in all_ids])

    print >>stderr, "done."


    # Define objective: maximize score
    objective = [
        'score', tolerance, 'max'
    ]


    print >>stderr, "Solving problem (may take a while) ..."

    # Construct problem
    p = KSP(objective, players, constraints=constraints, name='ksp_mop')

    # Run optimizer
    r = p.solve(solver, iprint=1, nProc=2)

    return (r, players)





def print_results(r, players):
    '''Take results object and players pool and print human-readable results'''
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
    row_format= u"{:<15}{:<15}{:<15}{:<14}{:^6}{:<5}{:<7}"

    print row_format.format('First Name',
        'Last Name', 'Position', 'Starting', 'Capt.', 'Club', 'Salary')
    print row_format.format(*["---"]*7)

    total_cost = 0.
    for player in roster:
        total_cost += player['cost']
        print row_format.format(
            player['fname'].decode('utf8'),
            player['lname'].decode('utf8'),
            player['position'],
            player['bench'],
            "X" if player['captain'] else "",
            player['club'],
            player['cost'])

    under_budget = round(budget-total_cost)
    if under_budget == 0:
        under_budget = 0.

    print 
    print u"Total Cost:\t£", total_cost, "M"
    print u"Under budget:\t£", under_budget, "M"
    print





if __name__=='__main__':
    # Run from CLI

    # Defaults
    season = 2014
    tolerance = 1e-6
    budget = 100.
    bench = 1e-1
    adjustments = None
    score = "total_points"
    solver_lbl = 'glpk'  # could be interalg


    # Get CL params
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('-y', '--season', type=int, default=season,
        help="ESPN endpoint only currently supports 2014 season")
    parser.add_argument('-t', '--tolerance', type=float, default=tolerance,
        help="Fuzzy boundaries around optimal solution, default is 1e-6")
    parser.add_argument('-b', '--budget', type=float, default=budget,
        help="Salary cap in millions of pounds, default is 100")
    parser.add_argument('-e', '--bench', type=float, default=bench,
        help="Fraction of score to reduce substitutes by, default is 1/10")
    parser.add_argument('-a', '--adjustments', type=str, default=adjustments,
        help="List of adjustments to player worth (file name)")
    parser.add_argument('-s', '--score', type=str, default=score,
        help="Player stat to be used in determining player's worth")
    parser.add_argument('-S', '--solver', type=str, default=solver_lbl,
        help="Solver to use. Can be interalg or glpk, or other KSP solvers.")

    cli = parser.parse_args()

    # Read CLI params back into internal vars
    season = cli.season
    tolerance = cli.tolerance
    budget = cli.budget
    bench = cli.bench
    adjustments = cli.adjustments
    score = cli.score
    solver_lbl = cli.solver



    # Run optimizer
    r, players = optimize(season=season, tolerance=tolerance,
        budget=budget, bench=bench, adjustments=adjustments,
        score=score, solver=solver_lbl)

    # Output raw solution from openopt solver
    print >>stderr, "Best solution found:"
    pprint(r.xf)

    # Print tidied-up results
    os.system('clear')

    print_results(r, players)
    






