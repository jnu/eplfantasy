# -*-coding: utf8-*-
'''
optimize_roster.py 

Optimize a fantasy English Premier List roster.

---
Fetches stats from an EPL fantasy server and parses them via eplstats.py.
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
from sys import stderr, stdout, exit
import eplstats
import argparse
import os
import re
import codecs


# globals
roster_line_format= u"{:<15}{:<15}{:<15}{:<14}{:^6}{:<5}{:<7}"



def get_injured_list(fn, has_header=True):
    if not os.path.exists(fn):
        raise IOError("Injured list file `%s` does not exist" % fn)

    disabled_list = []

    with open(fn) as fh:

        for i, line in enumerate(fh.readlines()):
            if has_header and i==0:
                # Skip header line
                continue

            try:
                # Sloppy splitting. Should maybe use struct module.
                fname = line[:20].strip()
                lname = line[20:40].strip()
                club = line[40:50].strip()
                factor = float(line[50:70].strip())
                notes = line[70:].strip()

            except Exception as e:
                raise IOError("Injured list file `%s` is misformatted: %s" \
                    %(fn, e))

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
            disabled_list.append({
                'first_name' : fname,
                'last_name' : lname,
                'factor' : factor,
                'club' : club,
                'news' : notes
            })

    return disabled_list



def sanitize(s):
    try:
        s = s.encode('ascii', 'replace')
    except UnicodeDecodeError:
        s = s.decode('utf8').encode('ascii', 'replace')

    return re.sub(r'[^\w]', '', s.lower())




def player_in_roster(player, roster,
    first_name='first_name', last_name='last_name', club='club'):
    '''Try to find given player (Player object) in roster (list of dicts).
    Problem is hard because of possible variations in spelling, encoding, etc.
    Heuristics used are to first match club, then try some variations of the
    sanitized name.
    Returns the player dict if found in roster, otherwise None.'''
    fname = sanitize(player.first_name)
    lname = sanitize(player.last_name)
    pclub = sanitize(player.club)

    for _aplayer in roster:
        # Note : Right now the heuristics used for matching are *good enough*,
        # but they could be better.

        if sanitize(_aplayer[club]) == pclub:
            # Correct club
            _aln = sanitize(_aplayer[last_name])
            _afn = sanitize(_aplayer[first_name])

            if _aln==lname and _afn==fname:
                # Simple case: total match for first name, last name
                return _aplayer

            elif _aln==lname and len(fname)==0:
                # Helps match Brazilians, mostly
                return _aplayer

            elif _afn==fname and len(lname)==0:
                # Same as previous
                return _aplayer

            elif fname[:1]==_afn[:1] and _aln==lname:
                # First initial last name. Hopefully no collisions!
                return _aplayer

    return None




def get_adjustment(player, adjustments, threshold=1, silent=False):
    '''Determine whether player should be devalued at all. Find given
    player in the adjustments list. Try to match player names via several
    heuristics. Use threshold to ignore adjustments above a certain level.
    Useful e.g. if you don't want to devalue players who have a .75 chance
    of playing --- these people could be back for the rest of the season.'''
    adj = 1.

    adj_player = player_in_roster(player, adjustments)

    if adj_player is not None:
        adj = adj_player['factor']

    if adj >= threshold:
        adj = 1.

    if not silent and adj!=1.:
        print >>stderr, " * Ignoring %s %s (%s) ~ %s" % \
        (
            adj_player['first_name'],
            adj_player['last_name'],
            adj_player['club'],
            adj_player['news']
        )

    return adj






def get_player_stats(score='total_points',
    season=2014, benchfrac=.1, adjustments=None,
    source='espn', username='', password='', threshold=1.):
    '''Get all the stats from ESPN.com and format them in the manner
    expected by the optimizer.
    Params:
     score       Can be attribute of Player or callable expecting Player as arg
     season      season to get stats for from ESPN
     benchfrac   Fraction of points awarded to substitutes
     adjustments Externally defined adjustments to player worth (injuries etc.)
    '''
    players = []

    # Keyword arguments are named after command line arguments.
    # adjustments really refers to the file name of the adjustments file
    # Internally adjustments should refer to the list of the adjustments
    adjfile = adjustments
    adjustments = None

    _positions = ['forwards', 'midfielders', 'defenders', 'keepers']
    _id = 0
    _uid = 990000

    downloader = eplstats.Downloader(source=source,
        username=username, password=password)

    for position in _positions:
        print >>stderr, "  Getting stats about %s ..." % position
        _players = downloader.get(position,
            source=source, season=season, adjustments=adjfile)


        # Get adjustments, if a file is given
        if adjfile is not None and adjustments is None:
            # Don't reparse adjustments file every run.
            adjustments = get_injured_list(adjfile)


        for player in _players:
            _id += 1

            # Find any external adjustment factoring to player worth
            adj_factor = 1.

            if adjustments is not None:
                adj_factor = get_adjustment(player, adjustments,
                    threshold=threshold)

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
    adjustments=None, score="total_points", solver="glpk",
    username='', password='', source='espn', threshold=1., nosolve=False):
    '''Configure and run KSP solver with given parameters. Returns openopt's
    solution object'''

    # Get stats
    print >>stderr, "Getting current stats from %s ..." % source
    players = get_player_stats(season=season,
        benchfrac=bench, score=score, adjustments=adjustments,
        source=source, username=username, password=password,
        threshold=threshold)
    print >>stderr, "Finished getting stats."

    if nosolve:
        return None, players

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





def print_results(r, players, fh=stdout, print_cost=True, budget=100.):
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
    # Note: row_format is read from a global so it can be shared with other
    # modules.
    row_format = roster_line_format

    print >>fh, row_format.format('First Name',
        'Last Name', 'Position', 'Starting', 'Capt.', 'Club', 'Salary')
    print >>fh, row_format.format(*["---"]*7)

    total_cost = 0.
    for player in roster:
        total_cost += player['cost']
        print >>fh, row_format.format(
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

    if print_cost:
        print >>fh, ""
        print >>fh, u"Total Cost:\t£", total_cost, "M"
        print >>fh, u"Under budget:\t£", under_budget, "M"
        print >>fh, ""





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
    username = ''
    password = ''
    source = 'espn'
    threshold = 1.
    nosolve = False
    outfilename = None


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
    parser.add_argument('-u', '--username', type=str, default=username,
        help="Username (for official EPL site)")
    parser.add_argument('-p', '--password', type=str, default=password,
        help="Password (for official EPL site)")
    parser.add_argument('-w', '--source', type=str, default=source,
        help="Stats source website. ESPN and EPL are supported.")
    parser.add_argument('-r', '--threshold', type=float, default=threshold,
        help="Threshold for devaluing injured players at all")
    parser.add_argument('--nosolve', action="store_true",
        help="Don't execute the solver")
    parser.add_argument('-o', '--out', type=str, default=outfilename,
        help="File to write team roster to")


    cli = parser.parse_args()


    # Make certain that solver is available. Warn if trying / forced to use
    # interalg that GLPK is much better.
    solver_lbl = cli.solver.lower()
    if solver_lbl=='glpk':
        try:
            import glpk
        except ImportError:
            print >>stderr, "Warning: can't find GLPK. Using interalg solver instead."
            solver_lbl = 'interalg'

    if solver_lbl=='interalg':
        print >>stderr, "Warning: interalg will take a long-ass time to solve this problem. Use GLPK if you can."



    # Run optimizer
    r, players = optimize(season=cli.season, tolerance=cli.tolerance,
        budget=cli.budget, bench=cli.bench, adjustments=cli.adjustments,
        score=cli.score, solver=solver_lbl, source=cli.source,
        username=cli.username, password=cli.password,
        threshold=cli.threshold, nosolve=cli.nosolve)

    # Output raw solution from openopt solver
    if r is not None:
        print >>stderr, "Best solution found:"
        pprint(r.xf)

        # Print tidied-up results
        os.system('clear')

        if cli.out is not None:
            # Write results to out file as necessary.
            with codecs.open(cli.out, "w", 'utf8') as fh:
                print_results(r, players, fh=fh, print_cost=False)
        # Print results to stdout
        print_results(r, players, budget=cli.budget)
    else:
        print >>stderr, "Players stats loaded in `players` variable"
    



