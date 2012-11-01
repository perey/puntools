#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Universe mapping tool for Naev.

Run this script from the root directory of your Naev source tree. It
reads the XML files in dat/ssys/ and outputs an SVG map to standard
output. Example usage:
    user@home:~/naev/$ jumpmap > map.svg

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

# Python 2 compatibility
from __future__ import division, print_function, unicode_literals

# Standard library imports.
from datetime import date
import sys

# Local imports.
from naevdata import SSystem
from dataloader import datafiles

def mapdata(ssystems):
    '''Extract mappable data from a list of star systems.

    Keyword arguments:
        ssystems -- A sequence object containing the star systems to be
            mapped (instances of naevdata.SSystem).
    Returns:
        A 4-tuple containing:
        * the map boundaries (a 4-tuple of x-minimum, x-maximum,
          y-minimum and y-maximum)
        * the system locations (a mapping object of system names to
          coordinates, given as 2-tuple x-y pairs)
        * the two-way jumps between systems (a sequence object of
          2-tuples holding the coordinates of the two ends, themselves
          given as 2-tuple x-y pairs)
        * the one-way jumps between systems (as above, but note that
          the two ends are ordered as origin then destination)

    '''
    syslocs = {}
    jumps_by_name = {}
    jumps = []
    jumps_oneway = []
    xmin = xmax = ymin = ymax = 0

    # Extract the data.
    for ssys in ssystems:
        # Note down the system name and location.
        syslocs[ssys.name] = ssys.pos
        # Note down any jumps it has. Ignore any that can't be entered from
        # here; they'll be recorded in the system at the other end.
        jumps_by_name[ssys.name] = list(dest for dest in ssys.jumps
                                        if not ssys.jumps[dest].exit_only)
        # Track the outermost systems.
        xmin = min(xmin, ssys.pos.x)
        xmax = max(xmax, ssys.pos.x)
        ymin = min(ymin, ssys.pos.y)
        ymax = max(ymax, ssys.pos.y)

    # Convert the jump data to a series of coordinates.
    for origin in jumps_by_name:
        for dest in jumps_by_name[origin]:
            if dest in jumps_by_name and origin in jumps_by_name[dest]:
                # Two-way jump.
                jumps.append((syslocs[origin], syslocs[dest]))
                # Don't duplicate jumps.
                jumps_by_name[dest].remove(origin)
            else:
                # One-way jump.
                jumps_oneway.append((syslocs[origin], syslocs[dest]))

    return ((xmin, xmax, ymin, ymax), syslocs, jumps, jumps_oneway)

def makemap(ssystems, margin=10, sys_size=5, ssystem_colour="orange",
            jump_colour="grey", label_colour="black", label_font="serif",
            file=sys.stdout):
    '''Create an SVG map from a list of star systems.

    Keyword arguments:
        ssystems -- A sequence object containing the star systems to be
            mapped (instances of naevdata.SSystem).
        margin -- The margin width (in pixels) to put around the edges
            of the map. The default value is 10.
        sys_size -- The radius of the dot representing each star system.
            The default is 5.
        ssystem_colour, jump_colour, label_colour, label_font -- Control
            the appearance of the SVG output. The default appearance has
            orange star systems, grey jumps, and labels in black serif.
        file -- A file-like object to output the SVG to. Defaults to
            standard output.

    '''
    (xmin, xmax, ymin, ymax), systems, jumps, jumps_oneway = mapdata(ssystems)
    # Pad the bounds of the map and convert to SVG viewBox specs.
    LABEL_SPACE = 200
    svg_bounds = (xmin - margin, -ymax - margin,
                  xmax - xmin + 2 * margin + LABEL_SPACE,
                  ymax - ymin + 2 * margin)

    # Output the SVG file.
    print('<?xml version="1.0"?>')
    print('<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
          'baseProfile="tiny" width="{2}px" height="{3}px" '
          'viewBox="{0} {1} {2} {3}">'.format(*svg_bounds), file=file)
    print('<title>Naev universe map {}</title>'.format(date.today()),
          file=file)
##    print('<!-- {} -->'.format((xmin, xmax, ymin, ymax)))

    # Style the map.
    print('<defs>', file=file)
    print('<marker id="arrow" orient="auto" viewBox="-1 -2 4 4"', file=file)
    print('        markerWidth="8" markerHeight="8">', file=file)
    print('    <path d="M 0,0 -1,-2 3,0 -1,2 Z" '
          'fill="{}"/>'.format(jump_colour), file=file)
    print('</marker>', file=file)
    print('<style type="text/css"><![CDATA[', file=file)
    print('    g#jumps > path {{stroke: {}; '
          'stroke-width: 1}}'.format(jump_colour), file=file)
    print('    g#jumps > path.oneway {stroke-dasharray: 2,1;', file=file)
    print('                           marker-mid: url(#arrow)}', file=file)
    print('    g#systems > circle {{stroke: none; '
          'fill: {}}}'.format(ssystem_colour), file=file)
    print('    g#systems > text {{stroke: none; '
          'fill: {}; font-family: {}}}'.format(label_colour, label_font),
          file=file)
    print(']]></style>', file=file)
    print('</defs>', file=file)
    print(file=file)

    # Output the jumps first, so they're underneath the system markers.
    print('<g id="jumps">', file=file)
    for jump in jumps:
        print('    <path d="M{},{} {},{}"/>'.format(jump[0].x, -jump[0].y,
                                                    jump[1].x, -jump[1].y),
              file=file)
    for jump in jumps_oneway:
        print('    <path class="oneway"', file=file)
        print('          d="M{0},{1} l{2},{3} {2},{3}"'
              '/>'.format(jump[0].x,
                          -jump[0].y,
                          (jump[1].x - jump[0].x) // 2,
                          -(jump[1].y - jump[0].y) // 2),
              file=file)
    print('</g>', file=file)
    print(file=file)

    # Output the system markers.
    print('<g id="systems">', file=file)
    for name in systems:
        x, y = systems[name].coords
        print('    <circle cx="{}" cy="{}" r="{}"/>'.format(x, -y, sys_size),
              file=file)
        print('    <text x="{}" y="{}" font-size="{}"'.format(x + 2 * sys_size,
                                                              -y + sys_size,
                                                              3 * sys_size),
              file=file)
        print('    >{}</text>'.format(name), file=file)
    print('</g>', file=file)
    print(file=file)

    # And we're done!
    print('</svg>', file=file)

def main():
    '''Generate an SVG map and print it to standard output.

    The data files are assumed to be in ./dat/ssys/, relative to the
    current path, so this should be run from the root of the Naev
    source directory.

    '''
    ssystems = []
    for ssysfile in datafiles('SSystems'):
        # Parse each XML file into a SSystem object.
        try:
            ssystems.append(SSystem(ssysfile))
        except:
            print("Choked on '{}'".format(ssysfile), file=sys.stderr)
            raise
    makemap(ssystems)

if __name__ == '__main__':
    main()
