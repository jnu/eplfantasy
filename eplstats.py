#-*-coding:utf8-*-
'''
eplstats.py

Get basic English Premier League fantasy stats from remote sources.

---
Usage:
>>> downloader = eplstats.Downloader(
    source='premierleague',
    username='your@email.com',
    password='password'
)
>>> downloader.get(position)

---
Possible values of `position` are:
 * keepers
 * defenders
 * midfielders
 * forwards

Possible sources are:
 * premierleague            Official English Premier League website
 * espn                     ESPN Fantasy Soccer server

Note `premierleague` provides injury statistics as well.

Request returns list of all Players from remote server with most recent data.
Player instances definitely have the following attributes:
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

import urllib
import urllib2
import cookielib
import re
import json
from bs4 import BeautifulSoup as bs
from getpass import getpass
from sys import stderr, exit




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
    el = soup.find(tag, attrs={'id': id_})
    if el is not None:
        return el.text.encode('utf8')
    return ''

def get_by_class(soup, tag, class_):
    el = soup.find(tag, attrs={'class': class_})
    if el is not None:
        return el.text.encode('utf8')
    return ''

def get_by_tag(soup, tag):
    el = soup.find(tag)
    if el is not None:
        return el.text.encode('utf8')
    return ''










class Downloader(object):

    defaults = {
        'season' : 2014,
        'adjustments' : 'adjustments.txt'
    }

    _espn_data = {
        'url' : "http://games.espn.go.com/premier-fantasy/%d/en_GB/format/ajax/getPlayersTable?entryID=1&ssid=1&slotID=%d&filter=&view=&spid=39",
        'pos_id_map' : {
            'keepers': 1,
            'defenders' : 3,
            'midfielders' : 8,
            'forwards': 13
        }
    }

    _pl_data = {
        'login_url' : \
    'https://users.premierleague.com/PremierUser/j_spring_security_check',
        'url' : 'http://fantasy.premierleague.com/squad-selection/',
        'aliases' : {
            'now_cost' : 'cost',
            'second_name': 'last_name',
            'element_type_id' : 'position',
            'points_per_game' : 'average_points'
        },
        'transforms' : {
            'cost' : lambda c: c/10.,
            'position' : lambda i: {
                1: 'keepers',
                2: 'defenders',
                3: 'midfielders',
                4: 'forwards'
            }[i],
            'chance_of_playing_this_round' : \
                lambda c: c/100. if c is not None else 1.,
            'chance_of_playing_next_round' : \
                lambda c: c/100. if c is not None else 1.
        }
    }



    def __init__(self, source=None, username='', password=''):
        '''Source must be `espn` or `premierleague`.'''
        self.username = username
        self.password = password

        self._cache = dict()

        self.cookiejar = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(debuglevel=0),
            urllib2.HTTPSHandler(debuglevel=0),
            urllib2.HTTPCookieProcessor(self.cookiejar)
        )

        self.opener.addheaders = [
            ('User-agent', 'Mozilla/5.0')
        ]



    def get(self, position, source=None, season=None, adjustments=None):
        '''Retrieve data from remote site for given position'''
        if season is None:
            season = self.defaults['season']

        if adjustments is None:
            adjustments = self.defaults['adjustments']

        if source is None:
            source = self.source

        source = source.lower().strip()

        if source=='espn':
            return self.get_espn(position, season)
        elif source=='pl' or source=='premierleague':
            return self.get_pl(position, season, adjustments)
        else:
            raise NotImplemented("Unrecognized stats source `%s`" % source)



    def login_to_pl(self, username=None, password=None):
        '''Log in to Premier League fantasy website'''
        if username is None:
            username = self.username
        if password is None:
            password = self.password

        # Build request
        data = {
            'j_username' : username,
            'j_password' : password,
            'redirectUrl' : ''
        }

        req = urllib2.Request(self._pl_data['login_url'],
            urllib.urlencode(data))

        # Execute request, hopefully will set a cookie when logged in
        success = True
        try:
            html = self.opener\
                .open(self._pl_data['login_url'], urllib.urlencode(data))\
                .read()

            # Verify success
            soup = bs(html)
            e = soup.find('label',
                attrs={'class':'error', 'for':'j_password'})
            if e is not None:
                raise AccessError("Login failed: %s" \
                    % e.text.encode('ascii', 'ignore'))
                success = False

        except urllib2.HTTPError as e:
            raise AccessError(\
"Login to Premier League website failed with error: %d (%s)" \
                % (e.code, str(e.reason)))
            success = False

        return success

    def interpret_pl_data(self, data):
        '''Take raw data from the website as dict (via json) and expand it
        into more sensible player data.'''
        raw_player_data = data['elInfo']
        field_map = data['elStat']
        aliases = self._pl_data['aliases']
        transforms = self._pl_data['transforms']

        # Create list of field labels
        field_labels = []
        for key, val in field_map.iteritems():
            while len(field_labels) <= val:
                field_labels.append(len(field_labels)-1)

            if key in aliases:
                # Some keys should be renamed to play nice with optimizer
                key = aliases[key]


            field_labels[val] = key

        players = []
        for player_data_list in raw_player_data:
            try:
                new_player = Player()

                for i, value in enumerate(player_data_list):
                    field = field_labels[i]

                    if field in transforms:
                        # Apply transformation to value if needed
                        value = transforms[field](value)

                    setattr(new_player, field, value)

                players.append(new_player)

            except TypeError:
                # There is at least one NoneType that will be encountered.
                # Ignore it.
                pass

        return players



    def get_pl(self, position, season=None, adjustments=None):
        '''Get players / stats for given position, saving adjustments in
        given file.'''
        if season is None:
            season = self.defaults['season']
        if adjustments is None:
            adjustments = self.defaults['adjustments']

        player_data = dict()

        if 'pldata' in self._cache:
            # Pl data is cached to limit server load
            player_data = self._cache['pldata']
        else:
            # Try to connect to PL website 
            html = ''
            url = self._pl_data['url']
            try:
                html = self.opener.open(url)
            except urllib2.HTTPError as e:
                if hasattr(e, 'code') and e.code==403:
                    # Forbidden! Try to log in
                    print >>stderr, "Need to log in to Premier League website."

                    # Prompt for username / password as needed
                    if len(self.username)<1:
                        username = input("Username> ").strip()
                    else:
                        username = self.username

                    if len(self.password)<1:
                        password = getpass("Password> ").strip()
                    else:
                        password = self.password

                    # Attempt login 
                    print >>stderr, "Logging in ..."
                    try:
                        s=self.login_to_pl(username=username,password=password)
                    except Exception as er:
                        print >>stderr, "Error: %s" % str(er)
                        s = False
                    
                    if not s:
                        # couldn't log in.
                        print >>stderr, "Login did not succeed."
                        t = input("Try again? ").strip()

                        if (t+"es")[:3].lower() == 'yes':
                            self.get_pl(position,
                                season=season, adjustments=adjustments)
                        else:
                            exit(1)

                    else:
                        # Login worked out! Recurse.
                        self.username = username
                        self.password = password
                        self.get_pl(position,
                            season=season, adjustments=adjustments)
                else:
                    # A non-403 error was received from PL site
                    print >>stderr, "Can't access Premier League site: %s" \
                        % str(e)

                    t = input("Try again? ").strip()
                    if (t+"es")[:3].lower() == 'yes':
                        self.get_pl(position,
                            season=season, adjustments=adjustments)

            # Successfully loaded PL website in `html` variable
            soup = bs(html)

            # Pull out JSON data
            data_s = soup.find('script', attrs={'type':'application/json'})
            data = json.loads(data_s.text.encode('utf8'))

            # Comprehend data from the site
            player_data = self.interpret_pl_data(data)

            # now cache data
            self._cache['pldata'] = player_data

        # Now `player_data` has all the info from the website, and it
        # is well-formatted as instances of Player.
        if adjustments is not None:
            # Write adjustments to external file

            # Find players that need adjusting
            to_adjust = [p for p in player_data
                            if player_data.chance_of_playing_this_round<1.]

            with open(adjustments) as fh:
                row_format = u"{:<30}{:^15}{:<35}"
                print >>fh, row_format.format("Name", "Adjustment", "Notes")
                for player in to_adjust:
                    adj_name = (player.first_name + player.last_name)\
                                .strip().encode('ascii', 'ignore')
                    print >>fh, row_format.format(
                        adj_name,
                        player.chance_of_playing_this_round,
                        player.news
                    )

        # Return all players matching `position`
        position = position.lower()
        return [p for p in player_data if player_data['position']==position]






    def get_espn(self, position, season=2014):
        '''Get players / stats for given position in given season.
        IMPORTANT! Currently ESPN endpoint doesn't support any seasons other
        than the current one, 2014.'''
        base_url = self._espn_data['url']
        _pos_id_map = self._espn_data['pos_id_map']

        position = _pos_id_map.get(position, None)

        if position is None:
            raise ValueError("No position given")

        url = base_url % (season, position)

        html = self.opener.open(url).read()

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

            _ops = [f.strip(")") for f
                in get_by_class(row, 'span', 'player_opp').split("(")]
            np.opponent, np.place = _ops if len(_ops)==2 else ['Unknown']*2

            np.cap_change = toFloat(get_by_class(row, 'td','player_capChange'))

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






## -- Exceptions -- ##

def AccessError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)



