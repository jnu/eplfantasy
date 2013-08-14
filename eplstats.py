#-*-coding:utf8-*-
'''
eplstats.py

Get basic English Premier League fantasy stats from the ESPN server.

---
Usage:
>>> espnstats.get(position, season=2014)

---
Possible values of `position` are:
 * keepers
 * defenders
 * midfielders
 * forwards

Request returns list of all Players from ESPN server with most recent data.
Player instances have the following attributes:
 * first_name
 * last_name
 * total_points     (fantasy points, per ESPN's rules)
 * average_points   (average fantasy points per week, per ESPN's rules)
 * rank             (fantasy ranking, determined by ESPN)
 * club             (club for which player plays)
 * cost             (salary for player)
 * opponent         (coming week's opponent)
 * place            (coming week is home or away ("H" or "A"))
 * cap_change       (increase or decrease in salary, per floating cap rules)
 * ownership        (percent of fantasy league owning player, as decimal)
 * own_change       (percent increase or decrease of ownership, as decimal)

---
Accessor is functional as of August 13, 2013 but the ESPN endpoint is liable
to change without notice.

---
Joe Nudell
'''

import urllib2
import re
from bs4 import BeautifulSoup as bs


base_url = "http://games.espn.go.com/premier-fantasy/%d/en_GB/format/ajax/getPlayersTable?entryID=1&ssid=1&slotID=%d&filter=&view=&spid=39"

_pos_id_map = {
    'keepers': 1,
    'defenders' : 3,
    'midfielders' : 8,
    'forwards': 13
}


class Player(object):
    def __init__(self):
        self.first_name = ''
        self.last_name = ''
        self.total_points = 0
        self.average_points = 0.
        self.rank = 0
        self.club = ''
        self.cost = 0.
        self.opponent = ''
        self.place = ''
        self.cap_change = 0.
        self.own_change = 0.
        self.ownership = 0.

    def get(self, val, default=None):
        return self.__dict__.get(val, default)

    def __repr__(self):
        return "<Player %s %s (%s)>" % \
            (self.first_name, self.last_name, self.club)


def toInt(v):
    _d = re.sub(r'[^\d]', '', v)
    if not len(_d):
        _d = 0
    return int(_d)

def toFloat(v):
    _f = re.sub(r'[^\d\.]', '', v)
    if not len(_f):
        _f = 0.
    return float(_f)

def get_by_id(soup, tag, id_):
    return soup.find(tag, attrs={'id': id_}).text.encode('utf8')

def get_by_class(soup, tag, class_):
    return soup.find(tag, attrs={'class': class_}).text.encode('utf8')

def get_by_tag(soup, tag):
    return soup.find(tag).text.encode('utf8')



def get(position, season=2014):
    '''Get players / stats for given position in given season.
    IMPORTANT! Currently ESPN endpoint doesn't support any seasons other than
    the current one, 2014.'''

    position = _pos_id_map.get(position, None)

    if position is None:
        raise ValueError("No position given")

    url = base_url % (season, position)

    headers = {'User-Agent': 'Mozilla/5.0'}

    req = urllib2.Request(url, None, headers)
    html = urllib2.urlopen(req).read()

    soup = bs(html)

    rows = soup.find('tbody').find_all('tr')

    players = []

    for row in rows:
        # pluck some key info out of the rows, store it in a Player
        np = Player()

        np.first_name = get_by_id(row, 'span', 'pFN')
        np.last_name = get_by_id(row, 'span', 'pLN')
        np.total_points = toInt(get_by_class(row, 'td', 'st-fpts'))
        np.average_points = toFloat(get_by_class(row, 'td', 'st-favg'))
        np.rank = toInt(get_by_class(row, 'td', 'st-frnk'))
        np.club = get_by_class(row, 'span', 'player_team')
        np.cost = toFloat(get_by_class(row, 'td', 'player_cost'))

        np.opponent, np.place = [f.strip(")") for f
            in get_by_class(row, 'span', 'player_opp').split("(")]

        np.cap_change = toFloat(get_by_class(row, 'td', 'player_capChange'))

        try:
            np.own_change = toFloat(get_by_tag('em')) / 100.
        except:
            np.own_change = 0.

        np.ownership = toFloat(soup.find('td',
            attrs={'class':'st-frnk'})\
            .find_next('td')\
            .text.encode('utf8')) / 100.


        players.append(np)

    return players




