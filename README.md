EPL Fantasy Roster Optimizer
===

##Purpose

This application attempts to optimize the roster of a fantasy English Premier League team on ESPN's fantasy platform.

##Requirements
[OpenOpt](http://openopt.org/), with `pip install openopt`

[GLPK \(4.48\)][http://www.gnu.org/software/glpk/]. Build with GMP support enabledby running `./configure --with-gmp` first.

[CVXOPT](http://cvxopt.org/). Build with GLPK linked by making sure `setup.py` has `BUILD_GLPK = 1`. Also make sure that `GLPK_LIB_DIR` and `GLPK_INC_DIR` point to the correct places, which you'll have to determine by looking at the end of the output of GLPK's build messages.

[Python-GLPK](http://www.dcc.fc.up.pt/~jpp/code/python-glpk/). To build this from source you will need `PLY` via `pip install ply`, then [SWIG](http://www.swig.org/download.html). Then you should extract the Python-GLPK source and edit `src/swig/Makefile` so that the first line reads `PYVERS := "python2.7"` (or your version of Python2). Then run `make` in the `src/` directory. Ignore the errors that appear. Now copy `src/swig/glpkpi.py` to `src/python/glpkpi.py`. Finally, run `python src/setup.py install`.

Note you may need to run every install command as `sudo`.

[BeautifulSoup](http://www.crummy.com/software/BeautifulSoup/bs4/doc/) is used for parsing the stats from ESPN. Get it with `pip install beautifulsoup4`.

##Usage

Run `optimize_roster.py` on the terminal in \*nix without any additional arguments to get a basic team.

See `optimize_roster.py -h` for the specific parameters which may be adjusted on the command line.

##Output

    First Name     Last Name      Position       Starting      Capt. Club Salary 
    ---            ---            ---            ---            ---  ---  ---    
    Robin          Van Persie     forward        starter             MUN  10.0   
    Luis           Suárez         forward        starter             LIV  9.3    
    Luke           Moore          forward        sub                 SWC  4.4    
    Gareth         Bale           midfielder     starter             TOT  9.6    
    Theo           Walcott        midfielder     starter             ARS  8.3    
    Frank          Lampard        midfielder     starter             CHL  8.1    
    Michu                         midfielder     starter             SWC  7.7    
    Jordan         Ibe            midfielder     starter             LIV  4.9    
    John           Terry          defender       starter             CHL  6.8    
    Nacho          Monreal        defender       starter             ARS  6.5    
    Sebastien      Bassong        defender       sub                 NOR  5.5    
    Alexander      Büttner        defender       starter         X   MUN  5.0    
    Steven         Whittaker      defender       sub                 NOR  4.7    
    Mark           Schwarzer      keeper         starter             CHL  4.5    
    Lukasz         Fabianski      keeper         sub                 ARS  4.5    

    Total Cost: £ 99.8 M
    Under budget:   £ 0.2 M



##Remote Stats

The script accesses the same endpoint on ESPN's servers that they use to display the stats in the fantasy sports website. This is liable to change without notice, no guarantees it will work for ever. Additionally, it may not be acceptable to access this endpoint and manipulate their data without their consent.

Four requests are made to the ESPN server every time the script is run. Do not use remote data for development purposes.

##Credits, License
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
