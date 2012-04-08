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
        if x is not None and y is None:
            # Just the one argument. Treat it as an XML element with <x> and
            # <y> children whose contents are the respective coordinates.
            self.x = nodetext(x.getElementsByTagName('x')[0])
            self.y = nodetext(x.getElementsByTagName('y')[0])
        else:
            # Both arguments, or neither.
            self.x = x if x is None else float(x)
            self.y = y if y is None else float(y)
    @property
    def coords(self):
        return (self.x, self.y)


class Jump(Coords):
    def __init__(self, pos, hide=1.25, exit_only=False, dest='ignored'):
        super().__init__(*pos)
        self.hide = float(hide)
        self.exit_only = bool(exit_only)


class Nebula:
    def __init__(self, density=0.0, volatility=0.0):
        self.density = float(density)
        self.volatility = float(volatility)


class Presence:
    def __init__(self, faction=None, value=100.0, range_=0.0):
        self.faction = faction
        self.value = float(value)
        self.range = int(range_)


class Services:
    def __init__(self, bar=None, commodity=None, land=None, missions=False,
                 outfits=False, refuel=False, shipyard=False):
        self.bar = bar # None, or a string describing the bar.
        # Note that the argument name is "commodity", to match the XML tag,
        # but the object attribute is named "commodities".
        self.commodities = None if commodity is None else set(commodity)
        self.land = land # None, or a string detailing who can land.
        self.missions = bool(missions)
        self.outfits = bool(outfits)
        self.refuel = bool(refuel)
        self.shipyard = bool(shipyard)


class Asset:
    def __init__(self, filename):
        if filename is None:
            # Create an empty, virtual asset.
            self.description = ''
            self.gfx = {}
            self.hide = 0.0
            self.population = 0
            self.pos = Coords()
            self.presence = Presence()
            self.services = Services()
            self.virtual = True
            self.world_class = None
        else:
            # Read the asset from the given file.
            with open(filename) as f:
                # Grab the elements we want.
                doc = xml.dom.minidom.parse(f)
                # Don't index any of these NodeLists yet (they may not exist).
                general = doc.getElementsByTagName('general')
                gfx = doc.getElementsByTagName('GFX')
                pos = doc.getElementsByTagName('pos')
                presence = doc.getElementsByTagName('presence')
                techs = doc.getElementsByTagName('tech')
                virtual = doc.getElementsByTagName('virtual')

                # Set the asset's position, graphics, and virtual-ness.
                self.pos = (Coords() if not pos else Coords(pos[0]))
                self.gfx = ({} if not gfx else
                            dict((child.tagName, nodetext(child))
                                  for child in gfx[0].childNodes
                                  if child.nodeType == child.ELEMENT_NODE))
                self.virtual = bool(virtual)

                # Extract the faction presence data.
                pres_data = ({} if not presence else
                             dict(('range_' if child.tagName == 'range'
                                   else child.tagName, nodetext(child))
                                  for child in presence[0].childNodes
                                  if child.nodeType == child.ELEMENT_NODE))
                self.presence = Presence(**pres_data)

                # Extract the list of technologies, each of which is an <item>
                # under the <tech> element.
                self.techs = set()
                if techs:
                    for tech in techs[0].getElementsByTagName('item'):
                        self.techs.add(nodetext(tech))

                # Extract the <general> information. Initialise each one just
                # in case it (or the whole of <general>) is absent.
                bar_desc = None
                commodities = None
                self.description = ''
                self.hide = 0.0
                self.population = 0
                self.services = None
                self.world_class = None

                # Do we even have a <general> element?
                if general:
                    for child in general[0].childNodes:
                        # We're only interested in child elements.
                        if child.nodeType != child.ELEMENT_NODE:
                            continue

                        if child.tagName == 'bar':
                            bar_desc = nodetext(child)
                        elif child.tagName == 'commodities':
                            # Get the set of child <commodity> nodes' content.
                            c_nodes = child.getElementsByTagName('commodity')
                            commodities = set(nodetext(c) for c in c_nodes)
                        elif child.tagName == 'services':
                            # Find which service type elements are present and
                            # get their content (if any -- most will be empty).
                            services = {}
                            for service in child.childNodes:
                                if service.nodeType != service.ELEMENT_NODE:
                                    continue
                                services[service.tagName] = nodetext(service)

                            # An empty <land> tag means anyone can land.
                            try:
                                if services['land'] == '':
                                    services['land'] = 'any'
                            except KeyError:
                                # An absent <land> tag means no-one can land.
                                pass

                            # Build the Services object.
                            self.services = Services(**services)
                        else:
                            # Everything else is just defined by its content.
                            try:
                                child_type = {'population': int,
                                              'hide': float}[child.tagName]
                            except KeyError:
                                child_type = str
                            self.__setattr__('world_class'
                                             if child.tagName == 'class'
                                             else child.tagName,
                                             child_type(nodetext(child)))
                # Finalise the list of services.
                if self.services is None:
                    self.services = Services()
                else:
                    # Put the bar description into the services -- if there is
                    # a bar there! If there isn't, the text is discarded.
                    if bar_desc is not None and self.services.bar is not None:
                        self.services.bar = bar_desc
                    # Put the commodities list into the services -- again, only
                    # if there are commodities traded here.
                    if (commodities is not None and
                        self.services.commodities is not None):
                        self.services.commodities = commodities


class SSystem:
    def __init__(self, filename=None):
        if filename is None:
            # Create an empty star system.
            self.assets = set()
            self.interference = 0.0
            self.jumps = {}
            self.name = ''
            self.nebula = Nebula()
            self.pos = Coords()
            self.radius = 0.0
            self.stars = 0
        else:
            # Read the star system from the given file.
            with open(filename) as f:
                # Grab the elements we want.
                doc = xml.dom.minidom.parse(f)
                assets = doc.getElementsByTagName('asset')
                general = doc.getElementsByTagName('general')[0]
                jumps = doc.getElementsByTagName('jump')
                pos = doc.getElementsByTagName('pos')[0]

                self.name = doc.documentElement.getAttribute('name')

                # Get the system's position, assets (planets and stations and
                # such), and jump points.
                self.pos = Coords(nodetext(pos.getElementsByTagName('x')[0]),
                                  nodetext(pos.getElementsByTagName('y')[0]))
                self.assets = set(nodetext(asset) for asset in assets)

                self.jumps = {}
                for jump in jumps:
                    autopos = jump.getElementsByTagName('autopos')
                    exit_only = jump.getElementsByTagName('exitonly')
                    # We don't index the NodeList of <pos> tags yet because it
                    # might be empty, if <autopos/> is present.
                    pos = jump.getElementsByTagName('pos')
                    jump_pos = ((None, None) if autopos
                                else (pos[0].getAttribute('x'),
                                      pos[0].getAttribute('y')))
                    hide = nodetext(jump.getElementsByTagName('hide')[0])

                    self.jumps[jump.getAttribute('target')] = Jump(jump_pos,
                                                                   hide,
                                                                   exit_only)

                # Extract the <general> information. Initialise each one just
                # in case it's missing.
                self.interference = 0.0
                self.nebula = None
                self.radius = 0.0
                self.stars = 0
                for child in general.childNodes:
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
                        # <stars> is an int; the rest are floats.
                        child_type = int if child.tagName == 'stars' else float
                        self.__setattr__(child.tagName, child_type(content))
                # And just in case <nebula> was absent...
                if self.nebula is None:
                    self.nebula = Nebula()
