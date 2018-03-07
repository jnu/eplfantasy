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
 * total_points     (fantasy points)
 * average_points   (average fantasy points per week)
 * club             (club for which player plays)
 * cost             (salary for player)
 * ownership        (percent of people who chose this player, as decimal)
 * position


Players from ESPN source in addition have the following fields:
 * rank             (fantasy ranking, determined by ESPN)
 * place            (coming week is home or away ("H" or "A"))
 * opponent         (coming week's opponent)
 * cap_change       (increase or decrease in salary, per floating cap rules)
 * own_change       (percent increase or decrease of ownership, as decimal)


Players from EPL Fantasy source in addition have the following fields:
 * added                            ISO timestamp
 * assists
 * bonus
 * bps
 * chance_of_playing_next_round
 * chance_of_playing_this_round
 * clean_sheets
 * event_cost                       (Note: in hundred thousands, not millions)
 * event_points
 * goals_conceded
 * goals_scored
 * last_season_points
 * max_cost                         (Note: in hundred thousands, not millions)
 * min_cost                         (Note: in hundred thousands, not millions)
 * minutes
 * news
 * news_added
 * news_return
 * news_updated
 * original_cost                    (Note: in hundred thousands, not millions)
 * own_goals
 * penalties_missed
 * penalties_saved
 * red_cards
 * saves
 * selected
 * status
 * transfers_balance
 * transfers_in
 * transfers_in_event
 * transfers_out
 * transfers_out_event
 * value_form
 * value_season
 * web_name
 * yellow_cards


---
Accessors are functional as of August 15, 2013 but the remote endpoints are
liable to change without notice. In addition, accessing these endpoints
programmatically and using the data obtained thereby may be in violation of
the remote site's terms of service.

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
            (
                self.first_name.encode('ascii', 'replace'),
                self.last_name.encode('ascii', 'replace'),
                self.club.encode('ascii','replace')
            )


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

def retryq(msg="Try again?"):
    t = raw_input("%s " % msg).strip()
    return (t+"es")[:3].lower() == 'yes'






class Downloader(object):

    defaults = {
        'season' : 2014
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
        'url' : 'https://fantasy.premierleague.com/a/squad/selection',
        'aliases' : {
            'now_cost' : 'cost',
            'second_name': 'last_name',
            'element_type_id' : 'position',
            'points_per_game' : 'average_points',
            'team_id' : 'club',
            'selected_by_percent' : 'ownership'
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
                lambda c: c/100. if c is not None else 1.,
            'club' : \
                lambda c: c,
            'ownership' : lambda c: c/100.
        }
    }



    def __init__(self, source=None, username='', password=''):
        '''Source must be `espn` or `premierleague`.'''
        self.username = username
        self.password = password
        self.source = source

        self._cache = dict()

        self.cookiejar = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(debuglevel=0),
            urllib2.HTTPSHandler(debuglevel=0),
            urllib2.HTTPCookieProcessor(self.cookiejar),
            urllib2.ProxyHandler()    # Auto-detect proxies
        )

        self.opener.addheaders = [
            ('User-agent', 'Mozilla/5.0')
        ]



    def get(self, position, source=None, season=None, adjustments=None):
        '''Retrieve data from remote site for given position'''
        if season is None:
            season = self.defaults['season']

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

        # Execute request, should set a cookie when logged in
        success = True
        try:
            html = self.opener\
                .open(self._pl_data['login_url'], urllib.urlencode(data))\
                .read()

        except urllib2.HTTPError as e:
            raise AccessError(\
"Login to Premier League website failed with error: %d (%s)" \
                % (e.code, str(e.reason)))
            success = False

        return success and self._pl_test_login(html)



    def interpret_pl_data(self, data):
        '''Take raw data from the website as dict (via json) and expand it
        into more sensible player data.'''
        raw_player_data = data['elInfo']
        field_map = data['elStat']
        team_map = data['teamInfo']
        # Install transform for team_map
        self._pl_data['transforms']['club'] = \
            lambda c: team_map[c]['short_name']

        aliases = self._pl_data['aliases']
        transforms = self._pl_data['transforms']

        self._cache['raw_data'] = data

        # Create list of field labels
        field_labels = []
        for key, val in field_map.iteritems():
            while len(field_labels) <= val:
                field_labels.append("f_%d" % (len(field_labels)-1))

            if key in aliases:
                # Some keys should be renamed to play nice with optimizer
                key = aliases[key]


            field_labels[val] = str(key)

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

            except TypeError as e:
                # There is at least one NoneType that will be encountered.
                # Ignore it.
                print >>stderr, "Warning: %s" % str(e)
                pass

        return players


    def _pl_test_login(self, html=None):
        url = self._pl_data['url']
        logged_in = True

        if html is None:
            # Site hasn't been accessed yet
            try:
                html = self.opener.open(url)
            except urllib2.HTTPError as e:
                if e.code==403:
                    logged_in = False
                else:
                    # A non-403 error was received from PL site. This means
                    # an unknown login status (there was a separate issue)
                    print >>stderr, "Can't access Premier League site: %s" \
                        % str(e)

                    return None

        # Now check HTML to see that there's no login form
        soup = bs(html)

        pwd = soup.find('input', attrs={"id": "id_password"})
        err = soup.find('p', attrs={'class': 'ismError'})
        err2 = soup.find('label',
                attrs={'class':'error', 'for':'j_password'})

        if pwd is not None or err is not None:
            logged_in = False

        if err2 is not None:
            print >>stderr, "Remote Error: %s" % err2.text.encode('utf8')
            logged_in = False

        # These are all the good heuristics so far
        return logged_in



    def _pl_login_mediator(self):
        '''Set up login to EPL site. Returns string retry, fail, or success.'''
        print >>stderr, "Need to log in to Premier League website."

        # Prompt for username / password as needed
        if len(self.username)<1:
            username = raw_input("Username> ").strip()
        else:
            username = self.username

        if len(self.password)<1:
            password = getpass("Password> ").strip()
        else:
            password = self.password

        # Attempt login 
        print >>stderr, "Logging in ..."
        try:
            s = self.login_to_pl(username=username, password=password)
        except Exception as er:
            print >>stderr, "Error: %s" % str(er)
            s = False
        
        if not s:
            # couldn't log in.
            print >>stderr, "Login did not succeed."
            retry = retryq()
            return "retry" if retry else "fail"

        else:
            # Login succeeded
            self.username = username
            self.password = password
            return "success"
    



    def get_pl(self, position, season=None, adjustments=None):
        '''Get players / stats for given position, saving adjustments in
        given file.'''

        if season is None:
            season = self.defaults['season']

        player_data = dict()

        if 'pldata' in self._cache:
            # Pl data is cached to limit server load
            player_data = self._cache['pldata']
        else:
            # Try to connect to PL website 
            
            # Check login
            logged_in = self._pl_test_login()
            retry = True

            while not logged_in and retry:
                resp = self._pl_login_mediator()

                if resp == 'success':
                    logged_in = True
                elif resp == 'retry':
                    print >>stderr, "Retrying login ..."
                    retry = True
                elif resp == 'fail':
                    print >>stderr, "Failed to get stats."
                    retry = False
                else:
                    print >>stderr, "Unknown response:", resp
                    retry = False

            if not logged_in:
                return []
            else:
                print >>stderr, "Successfully logged in."

            # Get the actual site
            html = self.opener.open(self._pl_data['url'])

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
            self._pl_write_adjustments(adjustments, player_data)

        # Return all players matching `position`
        position = position.lower()

        return [player for player in player_data if player.position==position]




    def _pl_write_adjustments(self, adjfile, player_data):
        # Write adjustments to external file

        # Find players that need adjusting
        to_adjust = [p for p in player_data
                        if p.chance_of_playing_next_round<1.]

        with open(adjfile, 'w') as fh:
            row_format = u"{:<20}{:<20}{:<10}{:<20}{:<60}"
            print >>fh, row_format.format(
                "First Name", "Last Name", "Club", "Adjustment", "Notes"
            )

            for player in to_adjust:
                print >>fh, row_format.format(
                    player.first_name.encode('ascii', 'replace'),
                    player.last_name.encode('ascii', 'replace'),
                    player.club,
                    player.chance_of_playing_next_round,
                    player.news
                )



    def get_espn(self, position, season=2014):
        '''Get players / stats for given position in given season.
        IMPORTANT! Currently ESPN endpoint doesn't support any seasons other
        than the current one, 2014.'''
        base_url = self._espn_data['url']
        _pos_id_map = self._espn_data['pos_id_map']
        pos_lbl = position

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
            np.position = pos_lbl

            _ops = [f.strip(")") for f
                in get_by_class(row, 'span', 'player_opp').split("(")]
            np.opponent, np.place = _ops if len(_ops)==2 else ['Unknown']*2

            np.cap_change = toFloat(get_by_class(row, 'td','player_capChange'))

            try:
                np.own_change = toFloat(get_by_tag('em')) / 100.
            except:
                np.own_change = 0.

            np.ownership = toFloat(row.find('td',
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



