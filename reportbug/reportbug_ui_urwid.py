# urwid user interface for reportbug
#   Written by Chris Lawrence <lawrencc@debian.org>
#   (C) 2001-06 Chris Lawrence
#
# This program is freely distributable per the following license:
#
##  Permission to use, copy, modify, and distribute this software and its
##  documentation for any purpose and without fee is hereby granted,
##  provided that the above copyright notice appears in all copies and that
##  both that copyright notice and this permission notice appear in
##  supporting documentation.
##
##  I DISCLAIM ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL
##  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN NO EVENT SHALL I
##  BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
##  DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
##  WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
##  ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
##  SOFTWARE.
#
# Portions of this file are licensed under the Lesser GNU Public License
# (LGPL) Version 2.1 or later.  On Debian systems, this license is available
# in /usr/share/common-licenses/LGPL
#
# $Id: reportbug_ui_urwid.py,v 1.3 2006-08-15 20:12:38 lawrencc Exp $

import commands, string, sys, re

import urwid.raw_display
import urwid

import reportbug

from reportbug_exceptions import *
from urlutils import launch_browser
from types import StringTypes

ISATTY = sys.stdin.isatty()

from reportbug_ui_text import spawn_editor

def ewrite(message, *args):
    if not ISATTY:
        return

    if args:
        sys.stderr.write(message % args)
    else:
        sys.stderr.write(message)

log_message = ewrite
display_failure = ewrite

# Start a urwid session
def initialize_urwid_ui():
    ui = urwid.raw_display.Screen()
    ui.register_palette(palette)
    return ui

# Widgets ripped mercilessly from urwid examples (dialog.py)
class buttonpush(Exception):
    pass

class SelectableText(urwid.Edit):
    def valid_char(self, ch):
        return False

class dialog(object):
    def __init__(self, message, body=None, width=None, height=None,
                 title='', long_message=''):
        self.body = body
        
        self.scrollmode=False
        if not body:
            if long_message:
                box = SelectableText(edit_text=long_message)
                box.set_edit_pos(0)
                self.body = body = urwid.ListBox([box])
                self.scrollmode=True
            else:
                self.body = body = urwid.Filler(urwid.Divider(), 'top')

        if not width:
            width = ('relative', 80)

        if not height:
            height = ('relative', 80)

        self.frame = urwid.Frame(body, focus_part='footer')
        if message:
            self.frame.header = urwid.Pile([urwid.Text(message),
                                            urwid.Divider()])
            
        w = self.frame
        # pad area around listbox
        w = urwid.Padding(w, ('fixed left',2), ('fixed right',2))
        w = urwid.Filler(w, ('fixed top',1), ('fixed bottom',1))
        w = urwid.AttrWrap(w, 'body')

        if title:
            w = urwid.Frame(w)
            w.header = urwid.Text( ('title', title) )
        
        # "shadow" effect
        w = urwid.Columns( [w, ('fixed', 1, urwid.AttrWrap( urwid.Filler(urwid.Text(('border',' ')), "top") ,'shadow'))])
        w = urwid.Frame( w, footer = urwid.AttrWrap(urwid.Text(('border',' ')),'shadow'))
        # outermost border area
        w = urwid.Padding(w, 'center', width )
        w = urwid.Filler(w, 'middle', height )
        w = urwid.AttrWrap( w, 'border' )
        self.view = w

    def add_buttons(self, buttons, default=0, vertical=False):
        l = []
        for name, exitcode in buttons:
            b = urwid.Button( name, self.button_press )
            b.exitcode = exitcode
            b = urwid.AttrWrap( b, 'selectable','focus' )
            l.append( b )

        if vertical:
            box = urwid.ListBox(l)
            box.set_focus(default or 0)
            self.buttons = urwid.Frame(urwid.AttrWrap(box, 'selectable'))
            self.frame.footer = urwid.BoxAdapter(self.buttons, min(len(l), 10))
        else:
            self.buttons = urwid.GridFlow(l, 10, 3, 1, 'center')
            self.buttons.set_focus(default or 0)
            self.frame.footer = urwid.Pile( [ urwid.Divider(), self.buttons ],
                                            focus_item = 1 )

    def button_press(self, button):
        raise buttonpush, button.exitcode

    def run(self):
        self.ui.set_mouse_tracking()
        size = self.ui.get_cols_rows()
        try:
            while True:
                canvas = self.view.render( size, focus=True )
                self.ui.draw_screen( size, canvas )
                keys = None
                while not keys: 
                    keys = self.ui.get_input()
                for k in keys:
                    if urwid.is_mouse_event(k):
                        event, button, col, row = k
                        self.view.mouse_event( size, 
                                               event, button, col, row,
                                               focus=True)
                    if k == 'window resize':
                        size = self.ui.get_cols_rows()
                    k = self.view.keypress( size, k )
                    if k:
                        self.unhandled_key( size, k)
        except buttonpush, e:
            return self.on_exit( e.args[0] )

    def on_exit(self, exitcode):
        return exitcode
    
    def unhandled_key(self, size, k):
        if k in ('tab', 'shift tab'):
            focus = self.frame.focus_part
            if focus == 'footer':
                self.frame.set_focus('body')
            else:
                self.frame.set_focus('footer')
        
        if k in ('up','page up', 'down', 'page down'):
            if self.scrollmode:
                self.frame.set_focus('body')
                self.body.keypress(size, k)
            elif k in ('up', 'page up'):
                self.frame.set_focus('body')
            else:
                self.frame.set_focus('footer')
                
        if k == 'enter':
            # pass enter to the "ok" button
            self.frame.set_focus('footer')
            self.view.keypress( size, k )

    def main(self, ui=None):
        if ui:
            self.ui = ui
        else:
            self.ui = initialize_urwid_ui()
        return self.ui.run_wrapper(self.run)

class displaybox(dialog):
    def show(self, ui=None):
        if ui:
            self.ui = ui
        else:
            self.ui = initialize_urwid_ui()
        size = self.ui.get_cols_rows()
        canvas = self.view.render( size, focus=True )
        self.ui.draw_screen( size, canvas )

class textentry(dialog):
    def __init__(self, text, width=None, height=None, multiline=False,
                 title=''):
        self.edit = urwid.Edit(multiline=multiline)
        body = urwid.ListBox([self.edit])
        body = urwid.AttrWrap(body, 'selectable', 'focustext')
        if not multiline:
            body = urwid.Pile( [('fixed', 1, body), urwid.Divider()] )
            body = urwid.Filler(body)

        dialog.__init__(self, text, body, width, height, title)

        self.frame.set_focus('body')

    def on_exit(self, exitcode):
        return exitcode, self.edit.get_edit_text()

class listdialog(dialog):
    def __init__(self, text, widgets, has_default=False, width=None,
                 height=None, title=''):
        l = []
        self.items = []
        for (w, label) in widgets:
            self.items.append(w)
            w = urwid.Columns( [('fixed', 12, w), 
                                urwid.Text(label)], 2 )
            w = urwid.AttrWrap(w, 'selectable','focus')
            l.append(w)

        lb = urwid.ListBox(l)
        lb = urwid.AttrWrap( lb, "selectable" )
        dialog.__init__(self, text, height=height, width=width, body=lb,
                        title=title)

        self.frame.set_focus('body')

    def on_exit(self, exitcode):
        """Print the tag of the item selected."""
        if exitcode:
            return exitcode, None

        for i in self.items:
            if i.get_state():
                return exitcode, i.get_label()
        return exitcode, None
		
class checklistdialog(listdialog):
    def on_exit(self, exitcode):
        """
        Mimick dialog(1)'s --checklist exit. 
        Put each checked item in double quotes with a trailing space.
        """
        if exitcode:
            return exitcode, []
        
        l = []
        for i in self.items:
            if i.get_state():
                l.append(i.get_label())
        return exitcode, l

def display_message(message, *args, **kwargs):
    if args:
        message = message % tuple(args)

    if 'title' in kwargs:
        title = kwargs['title']
    else:
        title = ''
        
    if 'ui' in kwargs:
        ui = kwargs['ui']
    else:
        ui = None

    # Rewrap the message
    chunks = re.split('\n\n+', message)
    chunks = [re.sub(r'\s+', ' ', x).strip() for x in chunks]
    message = '\n\n'.join(chunks).strip()

    box = displaybox('', long_message=message, title=title or reportbug.VERSION)
    box.show(ui)

def long_message(message, *args, **kwargs):
    if args:
        message = message % tuple(args)

    if 'title' in kwargs:
        title = kwargs['title']
    else:
        title = ''
        
    if 'ui' in kwargs:
        ui = kwargs['ui']
    else:
        ui = None
        
    # Rewrap the message
    chunks = re.split('\n\n+', message)
    chunks = [re.sub(r'\s+', ' ', x).strip() for x in chunks]
    message = '\n\n'.join(chunks).strip()

    box = dialog('', long_message=message, title=title or reportbug.VERSION,
                 ui=ui)
    box.add_buttons([ ("OK", 0) ])
    box.main(ui)

final_message = long_message
display_report = long_message

def select_options(msg, ok, help=None, allow_numbers=False, nowrap=False,
                   ui=None):
    box = dialog(msg, height=('relative', 80), title=reportbug.VERSION)
    if not help:
        help = {}

    buttons = []
    default = None
    for i, option in enumerate(ok):
        if option.isupper():
            default = i
            option = option.lower()
        buttons.append( (help.get(option, option), option) )

    box.add_buttons(buttons, default, vertical=True)
    result = box.main(ui)
    return result

def yes_no(msg, yeshelp, nohelp, default=True, nowrap=False, ui=None):
    box = dialog(msg, title=reportbug.VERSION)
    box.add_buttons([ ('Yes', True), ('No', False) ], default=1-int(default))
    result = box.main(ui)
    return result

def get_string(prompt, options=None, title=None, force_prompt=False,
               default=None, ui=None):
    if title:
        title = '%s: %s' % (reportbug.VERSION, title)
    else:
        title = reportbug.VERSION
    
    box = textentry(prompt, title=title)
    box.add_buttons([ ("OK", 0) ])
    code, text = box.main(ui)
    return text or default

def get_multiline(prompt, options=None, title=None, force_prompt=False,
                  ui=None):
    if title:
        title = '%s: %s' % (reportbug.VERSION, title)
    else:
        title = reportbug.VERSION

    box = textentry(prompt, multiline=True)
    box.add_buttons([ ("OK", 0) ])
    code, text = box.main(ui)
    l = text.split('\n')
    return l

def menu(par, options, prompt, default=None, title=None, any_ok=False,
         order=None, extras=None, multiple=False, empty_ok=False, ui=None):
    selected = {}

    if not extras:
        extras = []
    else:
        extras = list(extras)

    if not default:
        default = ''

    if title:
        title = '%s: %s' % (reportbug.VERSION, title)
    else:
        title = reportbug.VERSION

    if isinstance(options, dict):
        options = options.copy()
        # Convert to a list
        if order:
            olist = []
            for key in order:
                if options.has_key(key):
                    olist.append( (key, options[key]) )
                    del options[key]

            # Append anything out of order
            options = options.items()
            options.sort()
            for option in options:
                olist.append( option )
            options = olist
        else:
            options = options.items()
            options.sort()

    opts = []
    for option, desc in options:
        if desc:
            opts.append((option, re.sub(r'\s+', ' ', desc)))
        else:
            opts.append((option, desc))
    options = opts

    if multiple:
        widgets = [(urwid.CheckBox(option, state=(option == default)),
                    desc or '') for (option, desc) in options]
        box = checklistdialog(par, widgets, height=('relative', 80),
                              title=title)
        box.add_buttons( [('OK', 0)] )
        result, chosen = box.main(ui)
        return chosen

    # Single menu option only
    def label_button(option, desc):
        if not desc:
            return option
        else:
            return '%s: %s' % (option, desc)
    
    buttons = [(label_button(option, desc), option)
               for (option, desc) in options]

    buttons += [('Cancel', 'cancelbutton')]

    if any_ok:
        box = textentry(par, height=('relative', 80), title=title)
        buttons = [('Use the entry above', '')] + buttons
    else:
        box = dialog('', long_message=par, height=('relative', 80),
                     title=title)
    focus = 0
    if default:
        for i, opt in enumerate(options):
            if opt[0] == default:
                focus = i
                break
    
    box.add_buttons(buttons, focus, vertical=True)
    result = box.main(ui)
    if any_ok:
        result, text = result
        if result == 'cancelbutton':
            return None
        
        if not text:
            return result or ''
        return text
        
    if result == 'cancelbutton':
        return None
    return result

# A real file dialog would be nice here
def get_filename(prompt, title=None, force_prompt=False, default=''):
    return get_string(prompt, title=title, force_prompt=force_prompt,
                      default=default)

def select_multiple(par, options, prompt, title=None, order=None, extras=None):
    return menu(par, options, prompt, title=title, order=order, extras=extras,
                multiple=True, empty_ok=False)

# Things that are very UI dependent go here
def show_report(number, system, mirrors,
                http_proxy, screen=None, queryonly=False, title='',
                archived='no'):
    import debianbts

    ui = screen
    if not ui:
        ui = initialize_urwid_ui()

    sysinfo = debianbts.SYSTEMS[system]
    display_message('Retrieving report #%d from %s bug tracking system...', 
        number, sysinfo['name'], title=title, ui=ui)

    info = debianbts.get_report(number, system, mirrors=mirrors,
                                http_proxy=http_proxy, archived=archived)
    if not info:
        long_message('Bug report #%d not found.', number, title=title, ui=ui)
        return

    options = [('ok', 'OK'),
               ('moreinfo', 'More details (launch browser)'),
               ('quit', 'Quit')]
    if not queryonly:
        options.append(('submitmore', 'Submit more information'))
        
    while 1:
        (bugtitle, bodies) = info
        body = bodies[0]

        r = menu(body, prompt='', title=bugtitle, ui=ui, options=options)
        ui = None
        if not r or (r == 'ok'):
            break
        elif r == 'quit':
            return -1
        elif r == 'submitmore':
            return number

        launch_browser(debianbts.get_report_url(system, number, archived))
    return

def handle_bts_query(package, bts, mirrors=None, http_proxy="",
                     queryonly=0, screen=None, title="", archived='no',
                     source=0):
    raise UINotImplemented
    
    import debianbts

    sysinfo = debianbts.SYSTEMS[bts]
    root = sysinfo.get('btsroot')
    if not root:
        ewrite("%s bug tracking system has no web URL; bypassing query.\n",
               sysinfo['name'])
        return

    scr = screen
    if not scr:
        scr = newt_screen()
    
    if isinstance(package, StringTypes):
        if source:
            newt_infobox('Querying %s bug tracking system for reports on'
                         ' src:%s\n' % (debianbts.SYSTEMS[bts]['name'],
                                        package),
                         screen=scr, title=title)
        else:
            newt_infobox('Querying %s bug tracking system for reports on %s\n'%
                         (debianbts.SYSTEMS[bts]['name'], package),
                         screen=scr, title=title)
    else:
        newt_infobox('Querying %s bug tracking system for reports %s\n' %
                     (debianbts.SYSTEMS[bts]['name'], ' '.join([str(x) for x in
                                                                package])),
                     screen=scr, title=title)

    result = None
    try:
        (count, sectitle, hierarchy) = debianbts.get_reports(
            package, bts, mirrors=mirrors,
            http_proxy=http_proxy, archived=archived, source=source)

        if not count:
            scr.popWindow()
            if hierarchy == None:
                raise NoPackage
            else:
                raise NoBugs
        else:
            if count > 1:
                sectitle = '%d bug reports found' % (count)
            else:
                sectitle = '%d bug report found' % (count)

            list = []
            for (t, bugs) in hierarchy:
                bcount = len(bugs)
                list.append( ('', t) )
                for bug in bugs:
                    bits = string.split(bug[1:], ':', 1)
                    tag, info = bits
                    info = string.strip(info)
                    if not info:
                        info = '(no subject)'
                    list.append( (tag, info) )

            p = 1
            scr.popWindow()
            while True:
                info = newt_menu('Select a bug to read the report:', rows-6,
                                 columns-10, rows-15, list, sectitle,
                                 startpos=p, screen=scr)
                if not info:
                    break
                else:
                    p = i = 0
                    for (number, subject) in list:
                        if number == info: p = i
			i += 1

                    res = show_report(int(info), bts, mirrors,
                                      http_proxy, screen=scr,
                                      queryonly=queryonly, title=title)
                    if res:
                        result = res
                        break

    except (IOError, NoNetwork):
        scr.popWindow()
        newt_msgbox('Unable to connect to %s BTS.' % sysinfo['name'],
                    screen=scr, title=title)
    except NoPackage:
        #scr.popWindow()
        newt_msgbox('No record of this package found.',
                    screen=scr, title=title)

    if not screen:
        scr.finish()
    return result

palette = [
    ('body','black','light gray', 'standout'),
    ('border','black','dark blue'),
    ('shadow','white','black'),
    ('selectable','black', 'dark cyan'),
    ('focus','white','dark blue','bold'),
    ('focustext','light gray','dark blue'),
    ('title', 'dark red', 'light gray'),
    ]

def test():
    import time

    fp = sys.stdout

    long_message('This is a test.  This is only a test.\nPlease do not adjust your set.')
    time.sleep(1)
##     output = get_string('Tell me your name, biatch.')
##     print >> fp, output
##     output = get_multiline('List all of your aliases now.')
##     print >> fp, output
##     result = select_options('This is really lame', 'ynM', {
##         'y' : 'You bet', 'n' : 'Never!', 'm' : 'Maybe'})
##     print >> fp, result
##     yn = yes_no('Do you like green eggs and ham?', 'Yes sireee', 'No way!')
##     print >> fp, yn

    mailers = [(x, '') for x in reportbug.MUA.keys()]
    mailers.sort()
    mailer = menu('Choose a mailer for your report', mailers,
                  'Select mailer: ', default='mutt', empty_ok=True)
    print >> fp, mailer

    import debianbts

    tags = debianbts.TAGS.copy()
    tags.update(debianbts.CRITICAL_TAGS)
    tagorder = debianbts.TAGLIST + debianbts.CRITICAL_TAGLIST

    taglist = select_multiple(
        'Do any of the following apply to this report?', tags,
        'Please select tags: ', order=tagorder,
        extras=debianbts.EXTRA_TAGS)
    print >> fp, taglist

if __name__ == '__main__':
    test()