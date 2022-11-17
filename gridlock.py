#!/usr/bin/env python3
""" Gridlock -- Less choice, less chaos

Caveat emptor: This small tool uses RGBA visuals and therefore requires a
               compositing window manager.

Tile windows of your congested desktop onto a static grid. This tool should
be started by a hotkey or (additional) mouse button of your choice. When
activated, the currently active window can be moved and resized using a static
grid.

If your window manager does not allow to bind gridlock to your choice of
hotkey or mouse button, you may want to take a look at xbindkeys(1):

    <https://www.nongnu.org/xbindkeys/>

(c) 2022 Bjorn Fischer <bf@CeBiTec.Uni-Bielefeld.DE>

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk, Gdk, GdkX11, Wnck
import cairo

class Rect():

    def __init__(self, x1=-1, y1=-1, x2=-1, y2=-1):

        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def __bool__(self):
        return self.x1 >= 0 \
            and self.y1 >= 0 \
            and self.x2 >= 0 \
            and self.y2 >= 0

    def to_cairo(self, scale_x=1, scale_y=1):

        x1 = min(self.x1, self.x2)
        y1 = min(self.y1, self.y2)
        x2 = max(self.x1, self.x2)
        y2 = max(self.y1, self.y2)

        return (
            x1 * scale_x,
            y1 * scale_y,
            (1 + x2 - x1) * scale_x,
            (1 + y2 - y1) * scale_y,
            )

class GridLock(Gtk.Window):

    def __init__(self, active_window, cols=5, rows=4):

        super().__init__(title='Gridlock')

        self.active_window = active_window
        self.cols = cols
        self.rows = rows
        self.drag = False
        self.cursor_rect = Rect(-1, -1, -1, -1)

        screen = self.get_screen()                                                       
        visual = screen.get_rgba_visual()                                                
        if visual and screen.is_composited():                                            
            self.set_visual(visual)                                                      
        else:                                                                            
            raise RuntimeError('This application needs a compositor!')

        self.connect('destroy', Gtk.main_quit)
        self.fullscreen()

        self.set_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.BUTTON1_MOTION_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            )

        self.set_app_paintable(True)
        self.connect("key-press-event",self.on_key_press)
        self.connect('button_press_event', self.on_mouse_press)
        self.connect('button_release_event', self.on_mouse_release)
        self.connect("motion_notify_event", self.on_mouse_move)
        self.connect('draw', self.on_draw_window)

        overlay = Gtk.Overlay()

        self.cursor = Gtk.DrawingArea()
        self.cursor.connect('draw', self.on_draw_cursor)
        overlay.add(self.cursor)

        self.grid = Gtk.DrawingArea()
        self.grid.connect('draw', self.on_draw_grid)
        overlay.add_overlay(self.grid)

        self.add(overlay)

    def on_draw_window(self, window, ctx):
        ctx.set_source_rgba(0, 0, 0, 0)
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.paint()
        ctx.set_operator(cairo.OPERATOR_OVER)

    def on_draw_cursor(self, cursor, ctx):

        allocation = self.grid.get_allocation()
        cell_width = allocation.width // self.cols
        cell_height = allocation.height // self.rows

        if self.cursor_rect:
            ctx.set_source_rgba(1.0, 1.0, 1.0, .3)
            ctx.rectangle(
                *self.cursor_rect.to_cairo(cell_width, cell_height)
                )
            ctx.fill()

    def on_draw_grid(self, area, ctx):

        allocation = area.get_allocation()
        width = allocation.width
        height = allocation.height

        ctx.set_source_rgba(0, 0, 0, .2)
        ctx.rectangle(0, 0, width, height)
        ctx.fill()

        ctx.set_source_rgba(0, .4, 1, .8)
        ctx.set_line_width(4)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        for i in range(1, self.cols):
            x = i * width // self.cols
            ctx.move_to(x, 0)
            ctx.line_to(x, height-1)
            ctx.stroke()

        for i in range(1, self.rows):
            y = i * height // self.rows
            ctx.move_to(0, y)
            ctx.line_to(width-1, y)
            ctx.stroke()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_q or event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True

    def on_mouse_press(self, widget, event):
        if event.button == 1:
            self.drag = True
        else:
            Gtk.main_quit()

    def on_mouse_release(self, widget, event):
        self.drag = False

        allocation = self.grid.get_allocation()
        cell_width = allocation.width // self.cols
        cell_height = allocation.height // self.rows

        xid = self.get_window().get_xid()
        window = Wnck.Window.get(xid)
        (x, y, width, height) = self.cursor_rect.to_cairo(cell_width, cell_height)
        (root_x, root_y, root_width, root_height) = window.get_client_window_geometry()
        f = open("gridlock.log", "a")
        f.write("*****\n")
        f.write("window: {}\n".format(self.get_title()))
        f.write("x: {}\n".format(x))
        f.write("root_x: {}\n".format(root_x))
        f.write("y: {}\n".format(y))
        f.write("root_y: {}\n".format(root_y))
        f.write("width: {}\n".format(width))
        f.write("height: {}\n".format(height))
        f.close()

        self.active_window.set_geometry(
            Wnck.WindowGravity.NORTHWEST,
            Wnck.WindowMoveResizeMask.X
            | Wnck.WindowMoveResizeMask.Y
            | Wnck.WindowMoveResizeMask.WIDTH
            | Wnck.WindowMoveResizeMask.HEIGHT,
            x + root_x,
            y + root_y,
            width,
            height,
            )

        Gtk.main_quit()

    def on_mouse_move(self, widget, event):

        allocation = self.grid.get_allocation()
        cell_width = allocation.width // self.cols
        cell_height = allocation.height // self.rows

        if self.drag:
            self.cursor_rect.x2 = int(event.x / cell_width)
            self.cursor_rect.y2 = int(event.y / cell_height)

        else:
            self.cursor_rect.x1 = self.cursor_rect.x2 = int(event.x / cell_width)
            self.cursor_rect.y1 = self.cursor_rect.y2 = int(event.y / cell_height)

        self.cursor.queue_draw()

screen = Wnck.Screen.get_default()
screen.force_update()
active_window = screen.get_active_window()

if active_window is None:
    raise RuntimeError('Could not deterine active window')

window = GridLock(active_window)
window.show_all()
Gtk.main()

now = GdkX11.x11_get_server_time(
    GdkX11.X11Window.lookup_for_display(
        Gdk.Display.get_default(),
        GdkX11.x11_get_default_root_xwindow()
        )
    )
active_window.activate(now)

