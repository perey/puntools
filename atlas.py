#!/usr/bin/env python3

'''Universe atlas builder for Naev.

Run this script with the name of a database file created by the script
naevdb.py. It will read information from this database and output a set
of HTML files to an atlas/ subdirectory. Example usage:
    user@home:~/naev/$ atlas naev.db

'''

# Copyright © 2012 Tim Pederick.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Standard library imports.
from datetime import date, fromtimestamp
import os
import sqlite3 as db
import sys

# Local imports.
import naevdb

def scale_term(val, terms):
    '''Describe the relative scale or magnitude of a value.

    Keyword arguments:
        val -- The value to describe.
        terms -- A string naming the set of terms to be used.

    '''
    scale_ranges = {'radius': (('very small', 5000),
                               ('small', 10000),
                               ('medium', 20000),
                               ('large', 30000),
                               ('very large', None)),
                    'interference': (('none', 0),
                                     ('low', 100),
                                     ('moderate', 300),
                                     ('high', 500),
                                     ('very high', 750),
                                     ('extreme', None)),
                    'density': (('none', 0),
                                ('low', 100),
                                ('moderate', 250),
                                ('high', 450),
                                ('very high', 700),
                                ('extreme', None)),
                    'volatility': (('none', 0),
                                   ('low', 50),
                                   ('moderate', 100),
                                   ('high', 200),
                                   ('very high', 350),
                                   ('extreme', None)),
                    'stars': (('low', 200),
                              ('moderate', 400),
                              ('high', 600),
                              ('very high', None))}
    # Let the KeyError propagate upwards if the terms argument is unknown.
    ranges = scale_ranges[terms]

    for word, limit in ranges:
        # None signifies a default value.
        if limit is None or val <= limit:
            return word
    else:
        # Fell through without a match. Use the last one.
        return word

def ssysdesc(ssys, out):
    '''Write a description of a star system to an output file.

    The output is in HTML format and includes hyperlinks to in-system
    assets and connected systems.

    Keyword arguments:
        ssys -- The star system to describe. An instance of SSystem.
        out -- A file or file-like object, already opened for writing.

    '''
    # Start the HTML output.
    print('''<!DOCTYPE html>
<html lang="en">''', file=out)

    # Set metadata.
    print('''<head>
<title>{0.name} system - Naev Atlas</title>
</head>'''.format(ssys), file=out)

    # Describe the system.
    print('''<body>
<h1>{0.name}</h1>
<h2>Key data</h2>
  <dl>
    <dt>Coordinates</dt> <dd>({0.pos.x}, {0.pos.y})</dd>
    <dt>Interference</dt> <dd>{0.interference} ({1})</dd>
    <dt>Radius</dt> <dd>{0.radius} ({2})</dd>
    <dt>Nebula</dt> <dd>Density {0.nebula.density} ({3}),
                        volatility {0.nebula.volatility} ({4})</dd>
    <dt>Stars</dt> <dd>{0.stars} ({5})</dd>
  </dl>'''.format(ssys, scale_term(ssys.interference, 'interference'),
                  scale_term(ssys.radius, 'radius'),
                  scale_term(ssys.nebula.density, 'density'),
                  scale_term(ssys.interference, 'volatility'),
                  scale_term(ssys.stars, 'stars')),
          file=out)

    # Name the assets present here.
    # TODO: Link to them as well.
    print('<h2>Assets</h2>', file=out)
    print('  <ul>', file=out)
    for asset in ssys.assets:
        print('    <li><a href="../assets/{0}.html">'
              '{0}</a></li>'.format(asset), file=out)
    print('  </ul>', file=out)

    # Name the systems connected to here via hyperspace jumps.
    print('<h2>Jumps</h2>', file=out)
    print('  <ul>', file=out)
    for jumpname, jump in ssys.jumps.items():
        print('    <li><a href="{0}.html">{0}</a>'.format(jumpname),
              file=out)
        if jump.x is None:
            print('        (auto-positioned)', file=out)
        else:
            print('        @ ({0.x}, {0.y})'.format(jump), file=out)
        if jump.exit_only:
            print('        (exit-only)', file=out)
        print('    </li>', file=out)
    print('  </ul>', file=out)

    # Finish the HTML output.
    print('</body>\n</html>', file=out)

def assetdesc(asset, systems, out):
    '''Write a description of an asset to an output file.

    The output is in HTML format and includes a hyperlink to the system.
    TODO: No it doesn't. Not yet.

    Keyword arguments:
        assset -- The asset to describe. An instance of Asset.
        systems -- Names of star systems where this asset is present.
        out -- A file or file-like object, already opened for writing.

    '''
    # Start the HTML output.
    print('''<!DOCTYPE html>
<html lang="en">''', file=out)

    # Set metadata.
    print('<head>\n<title>{0.name} - Naev Atlas</title>\n'
          '</head>'.format(asset), file=out)

    # Describe the asset.
    print('<body>', file=out)
    print('<hgroup>\n<h1>{0.name}</h1>'.format(asset), file=out)
    print('<h2>(' + ('None' if len(systems) == 0 else
                     'Common' if len(systems) > 1 else
                     '<a href="../ssys/{0}.html">{0}</a>'.format(systems[0])) +
          ')</h2>\n</hgroup>', file=out)

    if asset.description:
        print('<p>{0.description}</p>'.format(asset), file=out)
    if asset.virtual:
        print('<p>Virtual asset.</p>', file=out)
    for purpose, image in asset.gfx.items():
        print('<p>{} image: {}</p>'.format(purpose.title(), image), file=out)

    # Provide data on this asset.
    print('''<h2>Key data</h2>
  <dl>
    <dt>Coordinates</dt> <dd>({0.pos.x}, {0.pos.y})</dd>
    <dt>Faction</dt> <dd>{0.presence.faction}
                         ({0.presence.value}, range {0.presence.range})</dd>
    <dt>Class</dt> <dd>{0.world_class}</dd>
    <dt>Population</dt> <dd>{0.population}</dd>
    <dt>Hide value</dt> <dd>{0.hide}</dd>
  </dl>'''.format(asset), file=out)

    # Describe services available here.
    print('''<h2>Services</h2>
  <dl>
    <dt>Landing rights</dt> <dd>{0.land}</dd>
    <dt>Spaceport bar</dt> <dd>{0.bar}</dd>
    <dt>Commodities</dt> <dd>{1}</dd>
    <dt>Refueling</dt> <dd>{0.refuel}</dd>
    <dt>Missions</dt> <dd>{0.missions}</dd>
    <dt>Shipyard</dt> <dd>{0.shipyard}</dd>
    <dt>Outfits</dt> <dd>{0.outfits}</dd>
  </dl>'''.format(asset.services,
                  'None' if asset.services.commodities is None else
                  ', '.join(asset.services.commodities)), file=out)

    # Finish the HTML output.
    print('</body>\n</html>', file=out)

def make_index(out):
    '''Write the main HTML page to an output file.

    Keyword arguments:
        out -- A file or file-like object, already opened for writing.

    '''
    # Start the HTML output.
    print('''<!DOCTYPE html>
<html lang="en">''', file=out)

    # Set metadata.
    print('<head>\n<title>Naev Atlas</title>\n</head>')

def main(dbfile):
    '''Generate an atlas of the Naev universe.'''
    atlasdir = os.path.join(os.curdir, 'atlas')
    ssysdir = os.path.join(atlasdir, 'ssys')
    assetdir = os.path.join(atlasdir, 'assets')
    # An OSError will be raised if the directory already exists, thus
    # preventing us from overwriting anything.
    os.mkdir(atlasdir)
    os.mkdir(ssysdir)
    os.mkdir(assetdir)

    # Create the main page of the atlas.
    with open(os.path.join(atlasdir, 'index.html'), 'w') as f:
        make_index(f)

    with db.connect(dbfile) as conn:
        ssystems = naevdb.get_ssystems(conn)

    assets = {}
    for assetfile in datafiles('Assets'):
        # Parse each XML file into an Asset object.
        asset = Asset(assetfile)
        assets[asset.name] = (asset, [])

    for ssys in ssystems:
        for asset in ssys.assets:
            assets[asset][1].append(ssys.name)

        with open(os.path.join(ssysdir, ssys.name + '.html'), 'w') as f:
            ssysdesc(ssys, f)

    for assetname in assets:
        asset, systems = assets[assetname]
        with open(os.path.join(assetdir, assetname + '.html'), 'w') as f:
            assetdesc(asset, systems, f)

if __name__ == '__main__':
    # Get the name of the database file.
    try:
        dbfile = sys.argv[1]
    except IndexError:
        # Default name.
        dbfile = 'naev.db'
    if not os.path.exists(dbfile):
        raise IOError("database file '{}' does not exist".format(dbfile))

    main(dbfile)
