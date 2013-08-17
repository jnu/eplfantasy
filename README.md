EPL Fantasy Roster Optimizer
===

### Purpose

This application attempts to optimize the roster of a fantasy English Premier League team.

### Supported fantasy platforms

The supported fantasy platforms are currently ESPN's and the official EPL site's.

The official EPL site provides information on injuries, suspensions, and other reasons why a player might not be playing. Even if you are interested in ESPN's platform, you should still grab the EPL data first to get this information about benched players:

    $ python optimize_roster.py --source premierleague --adjustments adjustments.txt --nosolve
    $ python optimize_roster.py --source espn --adjustments adjustments.txt

This will store the injuries from the EPL site in `adjustments.txt` but will not try to optimize the EPL site's fantasy team. The second command will take the adjustments from that text file and use them to devalue players in ESPN's fantasy game, then proceed to optimize for ESPN's game.

### Requirements

#### KSP Solving

* [OpenOpt](http://openopt.org/), with `pip install openopt`


#### Remote stat parsing
* [BeautifulSoup](http://www.crummy.com/software/BeautifulSoup/bs4/doc/) is used for parsing the stats from remote endpoints. Get it with `pip install beautifulsoup4`.

#### Speed-ups

You can use openopt's `interalg` to run the program with the solver included with `openopt`. Unfortunately this 1) does not guarantee you an optimal solution, and 2) takes so long it will make you cry.

The program will look for GLPK to do the heavy mathing instead of interalg. It can be a pain to install, but it'll save possibly hours of computation and aggravation.

Follow these steps to get GLPK working on *nix:

* [GLPK \(4.48\)](http://www.gnu.org/software/glpk/). Build with GMP support enabledby running `./configure --with-gmp` first.

* [CVXOPT](http://cvxopt.org/). Build with GLPK linked by making sure `setup.py` has `BUILD_GLPK = 1`. Also make sure that `GLPK_LIB_DIR` and `GLPK_INC_DIR` point to the correct places, which you'll have to determine by looking at the end of the output of GLPK's build messages.

* [Python-GLPK](http://www.dcc.fc.up.pt/~jpp/code/python-glpk/). To build this from source you will need `PLY` via `pip install ply`, then [SWIG](http://www.swig.org/download.html). Then you should extract the Python-GLPK source and edit `src/swig/Makefile` so that the first line reads `PYVERS := "python2.7"` (or your version of Python2). Then run `make` in the `src/` directory. Ignore the errors that appear. Now copy `src/swig/glpkpi.py` to `src/python/glpkpi.py`. Finally, run `python src/setup.py install`.

Note you may need to run every install command as `sudo`.

### Usage

Run `optimize_roster.py` on the terminal in \*nix without any additional arguments to get a basic optimized team on the default platform (ESPN).

Run `optimize_roster.py --source premierleague` to switch to EPL's fantasy platform.

See `optimize_roster.py -h` for the host of parameters that can be used to tweak the optimizer.

#### teamdiff

I also include the utility `teamdiff.py` which computes the similarity between teams. It currently uses a method similar to how cosine similarity is computed between documents using TF-IDF word frequences. Use it by providing two team rosters (as generated using `python optimize_roster.py ... --out roster.txt`) and the remote source of player stats as you would do when running `optimize_roster.py`.

Example:

    $ python teamdiff.py roster1.txt roster2.txt --source pl --username your@email.com --password password

The result will be a number in [0, 1] that is the cosine of the angle between the team vectors, incorporating the frequency that each player was chosen across the entire fantasy league team owners.

### Algorithm

The optimization problem is a sort of knapsack problem with a slew of constraints. Check the source for the specific constraints involved.

The value of each person is basically their total fantasy points per the fantasy game's stats. Fantasy points are doubled for the player you select as captain, and this is accounted for in searching for an optimal solution.

In addition, it is generally the case that bench players do not earn you many more points. Of course, they could, but there is no way to know that now. The program accounts for this by considering the fantasy points from a bench player as a fraction of their average points. You can adjust what fraction this should be. By default it is 1/10. A smaller fraction will mean less money is spent on your substitutes.

You can update most all parameters on the command line, including how a player's worth is calculated, how much they should be devalued for injuries, the total team budget, and more.

### Output

There will be a mess of status messages while the program is running.

Ultimately the program will give you a team roster it's recommended (assuming an optimal solution was found). The roster will have 15 players: three forwards, five midfielders, five defenders, and two keepers. It will tell you who to start and who to sit, which implicitly tells you what formation to use. It also tells you who the captain should be and how much money this will cost you.

Here's a sample output for the beginning of the 2013-14 season on the EPL official platform with a salary cap of £100 M (the default value). Note this is run without any adjustments; Gareth Bale is currently out with a foot injury and might not actually be a great choice for a starter, and definitely not captain (at least for the first couple weeks).

    First Name     Last Name      Position       Starting      Capt. Club Salary 
    ---            ---            ---            ---            ---  ---  ---    
    Dimitar        Berbatov       forward        starter             FUL  7.5    
    Rickie         Lambert        forward        starter             SOU  7.5    
    Luke           Moore          forward        sub                 SWA  4.5    
    Santi          Cazorla        midfielder     starter             ARS  10.0   
    Robert         Snodgrass      midfielder     starter             NOR  6.5    
    Jack           Colback        midfielder     sub                 SUN  4.5    
    Miguel         Michu          midfielder     starter             SWA  9.0    
    Gareth         Bale           midfielder     starter         X   TOT  12.0   
    Per            Mertesacker    defender       starter             ARS  5.5    
    Nathan         Baker          defender       sub                 AVL  4.0    
    Leighton       Baines         defender       starter             EVE  7.5    
    Glen           Johnson        defender       starter             LIV  6.0    
    Patrice        Evra           defender       starter             MUN  6.5    
    Mark           Schwarzer      keeper         starter             CHE  5.0    
    Kelvin         Davis          keeper         sub                 SOU  4.0 

    Total Cost:     £ 100.0 M
    Under budget:   £ 0.0 M



### Important notes about remote stats

* For the EPL official site you will need your own account. You will be prompted for your username and password when you try to access their stats, or you may present these parameters on the command line.

* The EPL access point currently only works while you haven't selected a team yet. Once you select a team on the account you're connecting through, the program will not be able to gather new data from the site.

* The use of statistics programmatically retrieved from the remote servers may be in violation of their terms of use. Please comply with these sites' terms of use.

* It is bad form to make unnecessary programmatic requests to websites without their explicit permission. Your IP may be filtered or your account suspended because of your actions in this respect. By design the program will make four requests to ESPN or at least three requests to EPL when you run it (depending on how many attempts you need to log on properly). Be conscious of how many requests you are making.

## Credits
All things in this repo are by Joe Nudell. See 3rd party libraries for their own respective authors and contributors, of which there are many.

## License
Copyright &copy; 2013, Joe Nudell

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met: 

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer. 
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies, 
either expressed or implied, of the FreeBSD Project.

See 3rd party libraries for their own licenses, which may differ from this one.
