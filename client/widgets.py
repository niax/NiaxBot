import logging
import urwid
import gevent
from datetime import datetime

class GEventEventLoop(object):
    def __init__(self):
        self._alarms = []
        self._watch_files = []
        self._idle_callbacks = {}
        self._idle_handle = 0
        self.logger = logging.getLogger("client.eventloop")
        self.running = False

    def alarm(self, seconds, callback):
        def _on_alarm():
            self.logger.debug("Alarm callback called: %d" % callback)
            self._alarms.remove(gevent.getcurrent())
            callback()
        eventlet = gevent.spawn_later(seconds, callback)
        self._alarms.append(eventlet)
        return eventlet             

    def remove_alarm(self, handle):
        handle.kill()
        self._alarms.remove(handle)
        return True

    def watch_file(self, fd, callback):
        def _file_callback():
            while True:
                self.logger.debug("Waiting for input on %d" % fd)
                gevent.socket.wait_read(fd)
                self.logger.debug("Done waiting for input on %d" % fd)
                callback()
        eventlet = gevent.spawn(_file_callback)
        self._watch_files.append(eventlet)
        self.logger.debug("Added watch for file monitor id: %d" % fd)
        return eventlet

    def remove_watch_file(self, handle):
        handle.kill()
        self._watch_files.remove(handle)
        return True

    def enter_idle(self, callback):
        self._idle_handle += 1
        self._idle_callbacks[self._idle_handle] = callback
        return self._idle_handle

    def remove_enter_idle(self, handle):
        try:
            del self._idle_callbacks[handle]
        except KeyError:
            return False
        return True

    def run(self):
        self.logger.debug("Running")
        self.running = True
        try:
            while self.running:
                self._loop()
            self.logger.debug("Quiting main loop")
            gevent.killall(self._alarms)
            gevent.killall(self._watch_files)
        except urwid.ExitMainLoop:
            pass # Pass over this as we're exiting as normal

    def stop(self):
        self.running = False

    def _loop(self):
        for handle in self._idle_callbacks:
            self._idle_callbacks[handle]()
        gevent.sleep(seconds=0.1)

class MainWidget(urwid.Frame):
    def __init__(self, client):
       self.client = client 
       self.inputbox = urwid.Edit(wrap = "clip")
       self.statuswindow = StatusWindow(client)
       self.windowmanager = WindowManager()
       self.windowmanager.add_window(self.statuswindow)
       self.windowmanager.set_active_window(1)
       self.windowmanager_widget = WindowManagerWidget(client, self.windowmanager)
       super(MainWidget, self).__init__(self.windowmanager_widget, footer=self.inputbox, focus_part="footer") 

    def keypress(self, size, key):
        if key == "enter":
            self.client.process_line(self.inputbox.get_edit_text())
            self.inputbox.set_edit_text("")
            key = None
        else:
            key = self.windowmanager.active_window().keypress(size, key)
        # Otherwise, pass to active widget
        if key != None:
            key = super(MainWidget, self).keypress(size, key)
        return key

class Window(object):
    def __init__(self):
        self.title = "Base Window. Override with something useful!"
        self.name = "Base Window"
        self.widget = urwid.SolidFill(fill_char='x')
        self.more = False

    def active(self):
        pass

    def inactive(self):
        pass

class TextWindow(Window):
    class View(urwid.BoxWidget):
        def __init__(self, window):
            self.window = window
            self.line_offset = 0
            self.lines_on_show = 0
            self.stick_bottom = False

        def page(self, travel):
            self.stick_bottom = False
            before = self.line_offset
            self.line_offset += travel * self.lines_on_show 
            if self.line_offset < 0:
                self.line_offset = 0
            self._invalidate()

        def cut_viewport(self, lines, attr, maxrow): 
            topline = self.line_offset
            bottomline = topline + maxrow

            # Ensure we don't scroll off the bounds
            if bottomline >= len(lines):
                bottomline = len(lines)
                topline = bottomline - maxrow
            if topline < 0:
                topline = 0

            if bottomline == len(lines):
                self.stick_bottom = True
                self.window.more = False # We're at view bottom so shouldn't be 'more'
            assert ((bottomline - topline) <= maxrow), 'Too many lines in viewport'
            logging.getLogger('client.render').debug('Top: %d Bottom: %d Offset: %d Len: %d' % (topline, bottomline, self.line_offset, len(lines)))
            self.line_offset = topline # Ensure lineoffset it kept up to date!
            return (lines[topline:bottomline], attr[topline:bottomline])

        def render(self, size, focus=False):
            (maxcol, maxrow) = size

            lines = reversed(self.window.lines) # Minor note, lines is inverted (element 0 is most recent)
            logging.getLogger('client.render').debug('Rendering %s' % self)
            str_lines = []
            attr_lines = []
            for line in lines:
                str_time = line.time.strftime('%H:%M:%S ') # TODO: Make timestamp configurable
                (offset, linesplit) = self.window.linesplit(line.content, maxcol - len(str_time))
                linesplit[0] = str_time + linesplit[0]
                lines_length = len(linesplit)
                combined_offset =  ' ' * (offset + len(str_time))
                i = 1
                while i < lines_length:
                    linesplit[i] = combined_offset + linesplit[i]
                    i += 1

                str_lines.extend(linesplit)

            if self.stick_bottom:
                self.line_offset = len(str_lines) - maxrow
                if self.line_offset < 0:
                    self.line_offset = 0

            (str_lines, attr_lines) = self.cut_viewport(str_lines, attr_lines, maxrow)
            self.lines_on_show = len(str_lines)
            for i in range(self.lines_on_show):
                if isinstance(str_lines[i], unicode):
                    str_lines[i] = str_lines[i].encode('ascii')
            #canvas = urwid.TextCanvas(text=str_lines, attr=attr_lines, maxcol=maxcol)
            canvas = urwid.TextCanvas(text=str_lines, maxcol=maxcol)
            compcanvas = urwid.CompositeCanvas(canv=urwid.SolidCanvas('-', maxcol, maxrow))
            if canvas.rows() != 0:
                compcanvas.overlay(urwid.CompositeCanvas(canv=canvas), 0, 0)
            return compcanvas

    class Line(object):
        def __init__(self, content):
            self.time = datetime.now()
            self.content = content


    def __init__(self):
        super(TextWindow, self).__init__()
        self.widget = TextWindow.View(self)
        self.lines = []

    def add_line(self, line):
        self.lines.insert(0, TextWindow.Line(line.strip())) # Push it at the front of the list
        if len(self.lines) > 2000 and self.widget.stick_bottom: # TODO: Make the scrollback configurable
            self.lines.pop() # Pop off the oldest entry
        if not self.widget.stick_bottom:
            self.more = True
        self.widget._invalidate()

    def linesplit(self, line, maxcol):
        lines = []
        while True:
            split_point = line.rfind(' ', 0, maxcol) # Find the last space before we have to split for columns
            if split_point == -1 or len(line) < maxcol:
                split_point = maxcol # If we don't have a space or we fit, give up and just split at the end
            lines.append(line[:split_point])
            line = line[split_point:].strip()
            if len(line) == 0:
                break
        return (0, lines)

    def keypress(self, size, key):
        if key == 'page up':
            self.widget.page(-1)
            key = None
        elif key == 'page down':
            self.widget.page(1)
            key = None
        return key
        
    

class StatusWindow(TextWindow):
    class WindowLogHandler(logging.Handler):
        def __init__(self, window):
            logging.Handler.__init__(self)
            self.window = window

        def emit(self, record):
            self.window.emit(self.format(record))

    CLIENT_MSG_PREFIX = "-!- PyRC: "

    def __init__(self, client):
        super(StatusWindow, self).__init__()
        self.title = client.VERSIONSTRING
        self.name = "Status"
        self.log_handler = StatusWindow.WindowLogHandler(self)
        self.log_handler.setLevel(logging.WARNING)
        self.log_handler.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s"))
        logging.getLogger('').addHandler(self.log_handler)
        self.emit('test')

    def client_message(self, message):
        self.add_line(StatusWindow.CLIENT_MSG_PREFIX + message)

    def emit(self, line):
        self.client_message(line)

    def linesplit(self, line, maxcol):
        result = super(StatusWindow, self).linesplit(line, maxcol - len(self.CLIENT_MSG_PREFIX))
        if line.startswith(self.CLIENT_MSG_PREFIX):
            result = (result[0] + len(self.CLIENT_MSG_PREFIX), result[1])
        return result
        
class QueryWindow(TextWindow):
    def __init__(self, query):
        self.query = query

class WindowManager(object):
    def __init__(self):
        self.windows = {}
        self.active_window_index = 0

    def add_window(self, window):
        self.windows[self._find_lowest_window()] = window

    def set_active_window(self, index):
        if self.active_window_index != 0:
            self.windows[self.active_window_index].inactive()
        self.active_window_index = index
        self.windows[self.active_window_index].active()

    def active_window(self):
        return self.windows[self.active_window_index] if self.active_window_index != 0 else None

    def _find_lowest_window(self):
        keys = self.windows.keys()
        keys.sort()
        last_window = 1
        for i in keys: # Find the first gap
            last_window += 1 # Move the current try along
            if last_window != i: # If it's equal, then it's not a gap, otherwise, it is!
                break
        return last_window


class WindowManagerWidget(urwid.Frame):
    def __init__(self, client, windowmanager):
        self.client = client
        self.windowmanager = windowmanager 
        self.statusline = StatusLineWidget()
        super(WindowManagerWidget, self).__init__(WindowWidget(self.windowmanager.active_window()), footer=urwid.AttrMap(self.statusline, 'status'))
        
        # Add statusbar items
        self.statusline.add_status_element(self._time)
        self.statusline.add_status_element(self._active)
        gevent.spawn(self._timed_update) # Spawn a timer to update the status bar

    def _time(self):
        now = datetime.now()
        return now.strftime("%H:%M:%S")

    def _active(self):
        return '%d:%s' % (self.windowmanager.active_window_index, self.windowmanager.active_window().name)

    def _timed_update(self):
        while self.client.running:
            self.statusline.refresh_content()
            self.client.mainloop.draw_screen() # Force a refresh (refresh typically happens on keypress, these don't come on keypress)
            gevent.sleep(seconds=1)

class WindowWidget(urwid.Frame):
    def __init__(self, window):
        self.window = window
        self.title_text = urwid.Text(' ' + window.title, wrap="clip")
        super(WindowWidget, self).__init__(window.widget, header=urwid.AttrMap(self.title_text, 'title'))




class StatusLineWidget(urwid.Columns):
    def __init__(self):
        self.left = urwid.Text('', wrap='clip')
        self.right = urwid.Text('', wrap='clip', align='right')
        self.status_elements = []
        super(StatusLineWidget, self).__init__([self.left, self.right])

    def set_has_more(self, value):
        if value:
            self.right.set_text(' ----more---- ')
        else:
            self.right.set_text('')
        self._invalidate()

    def add_status_element(self, function, pos=-1):
        if pos == -1:
            self.status_elements.append(function)
        else:
            self.status_elements.insert(pos, function)

    def refresh_content(self):
        items = []
        for function in self.status_elements:
            items.append(' ') # Spacing before element
            items.append(('status-seperator', '['))
            items.append(function())
            items.append(('status-seperator', ']'))
        self.left.set_text(items)
        self._invalidate()

