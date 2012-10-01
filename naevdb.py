#!/usr/bin/env python3

'''Store and retrieve Naev data in a SQLite database.'''

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
from collections import defaultdict
import os
import sqlite3 as db
import sys

# Local imports.
from dataloader import datafiles
from naevdata import Asset, Jump, SSystem

def adapt_boolean(boolean):
    '''Adapt (i.e. map from Python to SQLite3) boolean values.'''
    return int(boolean)
db.register_adapter(bool, adapt_boolean)

def convert_boolean(bool_column):
    '''Convert (i.e. map from SQLite3 to Python) boolean values.'''
    return bool(bool_column)
db.register_converter('BOOLEAN', convert_boolean)

def make_db(conn):
    '''Create an empty database.'''
    cur = conn.cursor()
    cur.execute('''CREATE TABLE SSystems (
                     SSysID INTEGER PRIMARY KEY AUTOINCREMENT
                   , SSysName TEXT NOT NULL
                   , SSysPosX REAL NOT NULL
                   , SSysPosY REAL NOT NULL
                   , SSysRadius REAL NOT NULL
                   , SSysStars INTEGER NOT NULL
                   , SSysInterference REAL NOT NULL
                   , SSysNebulaDensity REAL NOT NULL
                   , SSysNebulaVolatility REAL NOT NULL
                   )''')
    cur.execute('''CREATE TABLE Jumps (
                     JumpID INTEGER PRIMARY KEY AUTOINCREMENT
                   , JumpFromID INTEGER NOT NULL
                     REFERENCES SSystems
                       ON DELETE CASCADE
                   , JumpToID INTEGER NOT NULL
                     REFERENCES SSystems
                       ON DELETE CASCADE
                   , JumpPosX REAL
                   , JumpPosY REAL
                   , JumpHide REAL NOT NULL
                   , JumpIsExitOnly BOOLEAN NOT NULL
                   )''')
    cur.execute('''CREATE TABLE Assets (
                     AssetID INTEGER PRIMARY KEY AUTOINCREMENT
                   , AssetName TEXT UNIQUE NOT NULL
                   , SSysID INTEGER NOT NULL
                     REFERENCES SSystems
                       ON DELETE CASCADE
                   , AssetSpaceGfx TEXT NOT NULL
                   , AssetExteriorGfx TEXT NOT NULL
                   , AssetPosX REAL NOT NULL
                   , AssetPosY REAL NOT NULL
                   , AssetFaction TEXT
                   , AssetPresence REAL
                   , AssetPresenceRange INTEGER
                   , AssetClass TEXT NOT NULL
                   , AssetPopulation INTEGER NOT NULL
                   , AssetHide REAL NOT NULL
                   , AssetLandingRights TEXT
                   , AssetHasRefuel BOOLEAN
                   , AssetBarDesc TEXT
                   , AssetHasMissions BOOLEAN
                   , AssetHasOutfits BOOLEAN
                   , AssetHasShipyard BOOLEAN
                   )''')
    cur.execute('''CREATE TABLE VirtualAssets (
                     VAssetID INTEGER PRIMARY KEY AUTOINCREMENT
                   , VAssetName TEXT UNIQUE NOT NULL
                   , VAssetFaction TEXT NOT NULL
                   , VAssetPresence REAL NOT NULL
                   , VAssetPresenceRange INTEGER NOT NULL
                   )''')
    cur.execute('''CREATE TABLE SSysVAssets (
                     SSysID INTEGER NOT NULL
                     REFERENCES SSystems
                       ON DELETE CASCADE
                   , VAssetID INTEGER NOT NULL
                     REFERENCES VirtualAssets
                       ON DELETE CASCADE
                   , PRIMARY KEY (SSysID, VAssetID)
                   )''')

def store_ssys(conn, ssys):
    '''Store a star system in an open database.'''
    cur = conn.cursor()
    cur.execute('''INSERT INTO SSystems (
                     SSysName, SSysPosX, SSysPosY, SSysRadius, SSysStars
                   , SSysInterference, SSysNebulaDensity, SSysNebulaVolatility
                   ) VALUES (
                     ?, ?, ?, ?, ?
                   , ?, ?, ?
                   )''', (ssys.name, ssys.pos.x, ssys.pos.y, ssys.radius,
                          ssys.stars, ssys.interference, ssys.nebula.density,
                          ssys.nebula.volatility))

def store_jumps(conn, ssys):
    '''Store a star system's jump points in an open database.'''
    cur = conn.cursor()
    from_id = get_ssys_id(conn, ssys.name)
    for jumpdest, jump in ssys.jumps.items():
        to_id = get_ssys_id(conn, jumpdest)
        cur.execute('''INSERT INTO Jumps (
                         JumpFromID, JumpToID, JumpPosX, JumpPosY,
                         JumpHide, JumpIsExitOnly
                       ) VALUES (
                         ?, ?, ?, ?
                       , ?, ?
                       )''', (from_id, to_id, jump.x, jump.y,
                              jump.hide, jump.exit_only))

def store_asset(conn, asset, ssys=None):
    '''Store an asset (virtual or not) in an open database.'''
    cur = conn.cursor()
    if asset.virtual:
        cur.execute('''INSERT INTO VirtualAssets (
                         VAssetName, VAssetFaction
                       , VAssetPresence, VAssetPresenceRange
                       ) VALUES (
                         ?, ?, ?, ?
                       )''', (asset.name, asset.presence.faction,
                              asset.presence.value, asset.presence.range))
    else:
        cur.execute('''INSERT INTO Assets (
                         AssetName, SSysID, AssetSpaceGfx, AssetExteriorGfx
                       , AssetPosX, AssetPosY
                       , AssetFaction, AssetPresence, AssetPresenceRange
                       , AssetClass, AssetPopulation, AssetHide
                       , AssetLandingRights, AssetHasRefuel, AssetBarDesc
                       , AssetHasMissions, AssetHasOutfits, AssetHasShipyard
                       ) VALUES (
                         ?, ?, ?, ?
                       , ?, ?
                       , ?, ?, ?
                       , ?, ?, ?
                       , ?, ?, ?
                       , ?, ?, ?
                       )''',
                    (asset.name, get_ssys_id(conn, ssys),
                     asset.gfx.get('space'), asset.gfx.get('exterior'),
                     asset.pos.x, asset.pos.y, asset.presence.faction,
                     asset.presence.value, asset.presence.range,
                     asset.world_class, asset.population, asset.hide,
                     asset.services.land, asset.services.refuel,
                     asset.services.bar, asset.services.missions,
                     asset.services.outfits, asset.services.shipyard))

def store_vasset_location(conn, ssys, vasset):
    '''Record a location of a virtual asset in an open database.'''
    assert vasset.virtual
    cur = conn.cursor()
    cur.execute('''INSERT INTO SSysVAssets (SSysID, VAssetID)
                   VALUES (?, ?)''', (get_ssys_id(conn, ssys),
                                      get_asset_id(conn, vasset)))

def get_ssys_id(conn, ssys):
    '''Get the database ID for the given star system.'''
    try:
        # Get the name of the star system.
        name = ssys.name
    except AttributeError:
        # We were given just a name, not an SSystem object.
        name = ssys

    cur = conn.cursor()
    cur.execute('SELECT SSysID FROM SSystems WHERE SSysName = ?', (name,))
    row = cur.fetchone()
    return (None if row is None else row[0])

def get_asset_id(conn, asset, is_virtual=None):
    '''Get the database ID for the given asset.'''
    try:
        # Get the name of the asset.
        name = asset.name
    except AttributeError:
        # We were given just a name, not an Asset object.
        name = asset
    else:
        # If we have an Asset object, ignore the is_virtual argument.
        is_virtual = asset.virtual

    cur = conn.cursor()
    if is_virtual or is_virtual is None:
        # Try to find it in the virtual assets.
        cur.execute('SELECT VAssetID FROM VirtualAssets WHERE VAssetName = ?',
                    (name,))
        row = cur.fetchone()
        if row is not None:
            return row[0]

    # To have gotten to this point, either the we know the asset is not
    # virtual, or we don't know whether it is or not BUT we didn't find it in
    # the virtual assets, or we thought it was virtual BUT, again, we couldn't
    # find it. In any case, try to find it in the concrete assets.
    cur.execute('SELECT AssetID FROM Assets WHERE AssetName = ?', (name,))
    row = cur.fetchone()
    return (None if row is None else row[0])

def _get_ssys_extras(conn, ssys, ssys_id):
    '''Get star system data from outside the SSystems table.'''
    # Get the system jump data.
    cur = conn.cursor()
    cur.execute('''SELECT
                     s.SSysName
                   , j.JumpPosX, j.JumpPosY, j.JumpHide, j.JumpIsExitOnly
                   FROM
                     SSystems s JOIN
                     Jumps j ON s.SSysID = j.JumpToID
                   WHERE j.JumpFromID = ?''', (ssys_id,))
    for row in cur:
        ssys.jumps[row[0]] = Jump((row[1], row[2]), row[3], row[4])

    # Get the system asset data.
    cur.execute('SELECT AssetName FROM Assets WHERE SSysID = ?', (ssys_id,))
    for row in cur:
        ssys.assets.add(row[0])
    cur.execute('''SELECT v.VAssetName
                   FROM VirtualAssets v JOIN
                        SSysVAssets sv ON v.VAssetID = sv.VAssetID
                   WHERE sv.SSysID = ?''', (ssys_id,))
    for row in cur:
        ssys.assets.add(row[0])

def get_ssystems(conn):
    '''Get all star systems from an open database.'''
    ssystems = []
    cur = conn.cursor()
    cur.execute('''SELECT
                     SSysID, SSysPosX, SSysPosY, SSysRadius, SSysStars
                   , SSysInterference, SSysNebulaDensity, SSysNebulaVolatility
                   FROM SSystems''')
    for row in cur:
        ssys = SSystem()
        ssys.pos.x, ssys.pos.y = row['SSysPosX'], row['SSysPosY']
        ssys.radius, ssys.stars = row['SSysRadius'], row['SSysStars']
        ssys.interference = row['SSysInterference']
        ssys.nebula.density = row['SSysNebulaDensity']
        ssys.nebula.volatility = row['SSysNebulaDensity']

        ssys_id = row['SSysID']
        _get_ssys_extras(conn, ssys, ssys_id)

        ssystems.append(ssys)

    return ssystems

def get_ssys(conn, name):
    '''Get the named star system from an open database.'''
    ssys = SSystem()
    ssys.name = name

    cur = conn.cursor()
    # Get the basic system data.
    cur.execute('''SELECT
                     SSysID, SSysPosX, SSysPosY, SSysRadius, SSysStars
                   , SSysInterference, SSysNebulaDensity, SSysNebulaVolatility
                   FROM SSystems
                   WHERE SSysName = ?''', (name,))
    row = cur.fetchone()
    if row is None:
        # Nothing but a name!
        return ssys
    else:
        ssys_id = row['SSysID']
        ssys.pos.x, ssys.pos.y = row['SSysPosX'], row['SSysPosY']
        ssys.radius, ssys.stars = row['SSysRadius'], row['SSysStars']
        ssys.interference = row['SSysInterference']
        ssys.nebula.density = row['SSysNebulaDensity']
        ssys.nebula.volatility = row['SSysNebulaDensity']

    _get_ssys_extras(conn, ssys, ssys_id)

    return ssys

def get_ssys_presence(conn, name):
    '''Get the faction presences in the named system.'''
    presences = defaultdict(float)
    ssys_id = get_ssys_id(conn, name)
    cur = conn.cursor()

    # Get presence data from concrete assets.
    cur.execute('''SELECT AssetFaction, AssetPresence, AssetPresenceRange
                   FROM Assets
                   WHERE SSysID = ? AND AssetFaction IS NOT NULL''',
                (ssys_id,))
    for row in cur:
        presences[(row[0], row[2])] += row[1]

    # Get presence data from virtual assets.
    cur.execute('''SELECT
                     v.VAssetFaction
                   , v.VAssetPresence
                   , v.VAssetPresenceRange
                   FROM VirtualAssets v JOIN
                     SSysVAssets sv ON v.VAssetID = sv.VAssetID
                   WHERE sv.SSysID = ?''', (ssys_id,))
    for row in cur:
        presences[(row[0], row[2])] += row[1]

    return presences

def build_db(filename):
    '''Create and populate the Naev database.'''
    with db.connect(filename) as conn:
        make_db(conn)

        # Store the star systems.
        ssystems = []
        for ssysfile in datafiles('SSystems'):
            ssys = SSystem(ssysfile)
            ssystems.append(ssys)
            store_ssys(conn, ssys)

        # Store the assets.
        assets = []
        for assetfile in datafiles('Assets'):
            asset = Asset(assetfile)
            assets.append(asset)

            asset_ssys = None
            if not asset.virtual:
                # Find which system has the asset.
                for ssys in ssystems:
                    if asset.name in ssys.assets:
                        asset_ssys = ssys.name
                        break
                if asset_ssys is None:
                    print("Asset '{}' belongs to no "
                          "system. Skipped!".format(asset.name),
                          file=sys.stderr)
                    continue

            store_asset(conn, asset, asset_ssys)

        # Store the jumps between systems, and the locations of virtual assets.
        for ssys in ssystems:
            store_jumps(conn, ssys)
            for asset_name in ssys.assets:
                # Find the asset.
                for asset in assets:
                    if asset.name == asset_name:
                        this_asset = asset
                        break
                else:
                    # The named asset doesn't exist.
                    continue
                if this_asset.virtual:
                    store_vasset_location(conn, ssys, this_asset)

if __name__ == '__main__':
    # Create the database at the location given on the command line.
    try:
        filename = sys.argv[1]
    except IndexError:
        filename = 'naev.db'

    if os.path.exists(filename):
        raise IOError("output file '{}' already exists".format(filename))

    build_db(filename)
