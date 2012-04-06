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

from datetime import date
import glob
import os
import xml.sax

def null_fn(*args, **kwargs):
    pass

def reverse_state_table(states_transitions):
    '''Find the reverse transitions for a state table.

    Both the input and output state tables are represented as nested
    dictionaries. The keys at the first level are state names. At the
    second level, the keys are strings (or other objects) that trigger a
    transition. In the input table, the values are 2-tuples: a function
    to call (or even a list of functions), and the result state. The
    output table has no functions, just the result state.

    If more than one transition on the same trigger value leads to a
    state, the table is not invertible and a ValueError is raised.

    '''
    rev = {}
    for start_state, transitions in states_transitions.items():
        for trigger, result in transitions.items():
            function_to_ignore, result_state = result
            if result_state in rev:
                if trigger in rev[result_state]:
                    # Table is not invertible.
                    raise ValueError('multiple "{}" triggers can lead to the "'
                                     '{}" state'.format(trigger, result_state))
                else:
                    rev[result_state][trigger] = start_state
            else:
                rev[result_state] = {trigger: start_state}
    return rev

class Coords:
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y
    @property
    def coords(self):
        return (self.x, self.y)


class Nebula:
    def __init__(self, value=0.0, volatility=0.0):
        self.value = value
        self.volatility = volatility


class Jump(Coords):
    def __init__(self, pos, hide=1.25, exit_only=False, dest='ignored'):
        super().__init__(*pos)
        self.hide = hide
        self.exit_only = exit_only


class SSystem(xml.sax.ContentHandler):
    def __init__(self, filename):
        # Initialise attributes.
        self.name = None
        self.pos = None
        self.radius = 0.0
        self.stars = 0
        self.interference = 0.0
        self.nebula = None
        self.assets = set()
        self.jumps = {}

        # Ready the state tables.
        self.transitions = {None: {'ssys': (self.save_attribute('name'),
                                            'root')},
                            'root': {'general': (null_fn, 'general'),
                                     'pos': (null_fn, 'ssys_pos'),
                                     'assets': (null_fn, 'assets_list'),
                                     'jumps': (null_fn, 'jumps_list')},
                            'general': {'radius': (self.expect(float),
                                                   'general'),
                                        'stars': (self.expect(int), 'general'),
                                        'interference': (self.expect(float),
                                                         'general'),
                                        'nebula': ((self.hold('volatility'),
                                                    self.expect(float)),
                                                   'general')},
                            'ssys_pos': {'x': (self.expect(float),
                                               'ssys_pos'),
                                         'y': (self.expect(float),
                                               'ssys_pos')},
                            'assets_list': {'asset': (self.expect(str),
                                                      'assets_list')},
                            'jumps_list': {'jump': (self.hold('dest', 'target'),
                                                    'jump_point')},
                            'jump_point': {'autopos': (self.hold('pos', (None,
                                                                         None),
                                                                 False),
                                                       'jump_point'),
                                           'exitonly': (self.hold('exit_only',
                                                                  True, False),
                                                        'jump_point'),
                                           'pos': (self.hold('pos',
                                                                  ('x', 'y')),
                                                   'jump_point'),
                                           'hide': (self.expect(float),
                                                    'jump_hide')},
                            'jump_hide': {}}
        self.rv_transitions = {None: {},
                               'root': {'ssys': (null_fn, None)},
                               'general': {'general': (null_fn, 'root'),
                                           'radius': (self.save_pulled(),
                                                      'general'),
                                           'stars': (self.save_pulled(),
                                                     'general'),
                                           'interference': (self.save_pulled(),
                                                            'general'),
                                           'nebula': (self.save_nebula(),
                                                      'general')},
                               'ssys_pos': {'pos': (self.save_pos(),
                                                    'root'),
                                            'x': (self.hold_pulled(),
                                                  'ssys_pos'),
                                            'y': (self.hold_pulled(),
                                                  'ssys_pos')},
                               'assets_list': {'assets': (null_fn, 'root'),
                                               'asset': (self.save_asset(),
                                                         'assets_list')},
                               'jumps_list': {'jumps': (null_fn, 'root')},
                               'jump_point': {'jump': (self.save_jump(),
                                                       'jumps_list'),
                                              'autopos': (null_fn,
                                                          'jump_point'),
                                              'exitonly': (null_fn,
                                                           'jump_point'),
                                              'pos': (null_fn, 'jump_point')},
                               'jump_hide': {'hide': (self.hold_pulled(),
                                                      'jump_point')}}

        # Parse the XML to populate attributes.
        self._state = None
        self._expect = None
        self._content = None
        self._data_holding = None
        with open(filename) as f:
            parser = xml.sax.make_parser()
            parser.setContentHandler(self)
            parser.parse(f)

    def transition(self, trigger, data=None, reverse=False):
        table = self.rv_transitions if reverse else self.transitions

        # Sanity pre-check.
        assert self._state in table, 'stuck in state "{}"'.format(self._state)

        try:
            result = table[self._state][trigger]
        except KeyError:
            raise ValueError('trigger "{}" is invalid in state '
                             '"{}"'.format(trigger, self._state))
        function, new_state = result
        # The "function" could actually be a list of functions.
        try:
            for sub_fn in function:
                sub_fn(trigger, data)
        except TypeError:
            # Nope, just one function.
            function(trigger, data)
        self._state = new_state

        # Sanity post-check.
        assert self._state in table, ('state "{}" is a dead '
                                      'end'.format(self._state))

    def pull_content(self):
        result = self._expect(''.join(self._content))
        self._expect = None
        self._content = None
        return result

    # The next several functions are generic transition handlers.
    def expect(self, content_type):
        def expect_fn(name, attrs):
            self._content = []
            self._expect = content_type
        return expect_fn

    def hold(self, label, val=None, data_in_attrs=True):
        '''Create a function to hold some data until needed.'''
        if val is None and data_in_attrs:
            # The label we're using is the same as the XML attribute name.
            val = label

        def hold_fn(name, attrs):
            if self._data_holding is None:
                self._data_holding = {}

            # Is the data to hold in the XML element's attributes?
            if data_in_attrs:
                # We can save one attribute or several. If just one, val will
                # always be a string.
                if type(val) == str:
                    self._data_holding[label] = attrs[val]
                # If more than one, val will be a list of strings.
                else:
                    self._data_holding[label] = tuple(attrs[v] for v in val)
            else:
                # Nope, it's just some specified data. And since we're not
                # pulling it from the XML attributes, it could be anything.
                self._data_holding[label] = val
        return hold_fn

    def hold_pulled(self, label=None):
        def hold_fn(name, attrs):
            if self._data_holding is None:
                self._data_holding = {}
            n = name if label is None else label
            self._data_holding[n] = self.pull_content()
        return hold_fn

    def save_attribute(self, xml_name, obj_name=None):
        '''Create a function to set an attribute on this instance.'''
        if obj_name is None:
            obj_name = xml_name
        def save_fn(name, attrs):
            self.__setattr__(obj_name, attrs[xml_name])
        return save_fn

    def save_pulled(self, obj_name=None):
        '''Create a function to set an attribute to the content data.'''
        def save_fn(name, attrs):
            self.__setattr__(name if obj_name is None else obj_name,
                             self.pull_content())
        return save_fn

    # The rest of these functions are still transition handlers, but they're
    # one-shot functions that aren't worth making generic.
    def save_asset(self):
        '''Create a function to save an asset.'''
        def asset_fn(name, attrs):
            self.assets.add(self.pull_content())
        return asset_fn

    def save_jump(self):
        '''Create a function to save a Jump instance.'''
        def jump_fn(name, attrs):
            self.jumps[self._data_holding['dest']] = Jump(**self._data_holding)
            self._data_holding = None
        return jump_fn

    def save_nebula(self):
        def nebula_fn(name, attrs):
            self.nebula = Nebula(self.pull_content(), **self._data_holding)
            self._data_holding = None
        return nebula_fn

    def save_pos(self):
        def pos_fn(name, attrs):
            self.pos = Coords(**self._data_holding)
            self._data_holding = None
        return pos_fn

    # Finally, we implement the SAX event handlers.
    def startElement(self, name, attrs):
        self.transition(name, attrs)

    def endElement(self, name):
        self.transition(name, reverse=True)

    def characters(self, content):
        # Do we care about character data?
        if self._content is not None:
            # Yes!
            try:
                # The content is either bytes...
                self._content.append(content.decode())
            except AttributeError:
                # ...or a string.
                self._content.append(content)

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
        # Note down any jumps it has. Ignore any that can't be entered here.
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

def makemap(ssystems, margin=5, sys_size=5, ssystem_colour="orange",
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
        # Parse the XML file into a SSystem object.
        ssystems.append(SSystem(ssysfile))
    makemap(ssystems)

if __name__ == '__main__':
    main()
