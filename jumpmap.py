#!/usr/bin/env python3

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

# Standard library imports.
from datetime import date
import glob
import os

# Local imports.
from naevdata import SSystem

def mapdata(ssystems):
    '''Extract mappable data from a list of star systems.'''
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
            jump_colour="grey", label_colour="black", label_font="serif"):
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
          'viewBox="{0} {1} {2} {3}">'.format(*svg_bounds))
    print('<title>Naev universe map {}</title>'.format(date.today()))
    print('<!-- {} -->'.format((xmin, xmax, ymin, ymax)))

    # Style the map.
    print('<defs>')
    print('<marker id="arrow" orient="auto" viewBox="-1 -2 4 4"')
    print('        markerWidth="8" markerHeight="8">')
    print('    <path d="M 0,0 -1,-2 3,0 -1,2 Z" '
          'fill="{}"/>'.format(jump_colour))
    print('</marker>')
    print('<style type="text/css"><![CDATA[')
    print('    g#jumps > path {{stroke: {}; '
          'stroke-width: 1}}'.format(jump_colour))
    print('    g#jumps > path.oneway {stroke-dasharray: 2,1;')
    print('                           marker-mid: url(#arrow)}')
    print('    g#systems > circle {{stroke: none; '
          'fill: {}}}'.format(ssystem_colour))
    print('    g#systems > text {{stroke: none; '
          'fill: {}; font-family: {}}}'.format(label_colour, label_font))
    print(']]></style>')
    print('</defs>')
    print()

    # Output the jumps first, so they're underneath the system markers.
    print('<g id="jumps">')
    for jump in jumps:
        print('    <path d="M{},{} {},{}"/>'.format(jump[0].x, -jump[0].y,
                                                    jump[1].x, -jump[1].y))
    for jump in jumps_oneway:
        print('    <path class="oneway"')
        print('          d="M{0},{1} l{2},{3} {2},{3}"'
              '/>'.format(jump[0].x,
                          -jump[0].y,
                          (jump[1].x - jump[0].x) // 2,
                          -(jump[1].y - jump[0].y) // 2))
    print('</g>')
    print()

    # Output the system markers.
    print('<g id="systems">')
    for name in systems:
        x, y = systems[name].coords
        print('    <circle cx="{}" cy="{}" r="{}"/>'.format(x, -y, sys_size))
        
        print('    <text x="{}" y="{}" font-size="{}"'.format(x + 2 * sys_size,
                                                              -y + sys_size,
                                                              3 * sys_size))
        print('    >{}</text>'.format(name))
    print('</g>')
    print()

    # And we're done!
    print('</svg>')

def main():
    ssys_dir = os.path.join(os.curdir, 'dat', 'ssys')

    if not os.path.exists(ssys_dir):
        raise IOError('could not find directory dat/ssys/ (run this from the '
                      'root of your Naev source directory)')

    ssystems = []
    for ssysfile in glob.glob(os.path.join(ssys_dir, '*.xml')):
        # Parse each XML file into a SSystem object.
        ssystems.append(SSystem(ssysfile))
    makemap(ssystems)

if __name__ == '__main__':
    main()
