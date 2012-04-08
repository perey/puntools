#!/usr/bin/env python3

'''Naev data file tools.'''

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

import xml.dom.minidom

nodetext = lambda elem: ''.join(c.data for c in elem.childNodes
                                if c.nodeType == c.TEXT_NODE)

class Coords:
    def __init__(self, x=None, y=None):
        self.x = x if x is None else float(x)
        self.y = y if y is None else float(y)
    @property
    def coords(self):
        return (self.x, self.y)


class Nebula:
    def __init__(self, density=0.0, volatility=0.0):
        self.density = float(density)
        self.volatility = float(volatility)


class Jump(Coords):
    def __init__(self, pos, hide=1.25, exit_only=False, dest='ignored'):
        super().__init__(*pos)
        self.hide = float(hide)
        self.exit_only = bool(exit_only)


class SSystem:
    def __init__(self, filename):
        with open(filename) as f:
            doc = xml.dom.minidom.parse(f)
            self.name = doc.documentElement.getAttribute('name')

            # Extract the <general> information.
            for child in doc.getElementsByTagName('general')[0].childNodes:
                # We're only interested in child elements.
                if child.nodeType != child.ELEMENT_NODE:
                    continue

                content = nodetext(child)
                if child.tagName == 'nebula':
                    # The <nebula> tag has a couple of bits of info.
                    self.nebula = Nebula(content,
                                         child.getAttribute('volatility'))
                else:
                    # Everything else is just a single piece of content.
                    self.__setattr__(child.tagName,
                                     int(content) if child.tagName == 'stars'
                                     else float(content))

            # Extract the system's position.
            pos = doc.getElementsByTagName('pos')[0]
            self.pos = Coords(nodetext(pos.getElementsByTagName('x')[0]),
                              nodetext(pos.getElementsByTagName('y')[0]))

            # Extract the system's assets (planets and stations and such).
            self.assets = tuple(nodetext(asset)
                                for asset in doc.getElementsByTagName('asset'))

            # Extract the jump points out of this system.
            self.jumps = {}
            for jump in doc.getElementsByTagName('jump'):
                autopos = jump.getElementsByTagName('autopos')
                exit_only = jump.getElementsByTagName('exitonly')
                # We don't index the NodeList of <pos> tags yet because it
                # might be empty, if <autopos/> is present.
                pos = jump.getElementsByTagName('pos')
                jump_pos = ((None, None) if autopos
                            else (pos[0].getAttribute('x'),
                                  pos[0].getAttribute('y')))
                hide = nodetext(jump.getElementsByTagName('hide')[0])

                self.jumps[jump.getAttribute('target')] = Jump(jump_pos, hide,
                                                               exit_only)
