#!/usr/bin/env python3

import sys
import argparse
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk, Gdk, GdkX11, Wnck
import cairo

screen = Wnck.Screen.get_default()
screen.force_update()
active_window = screen.get_active_window()
active_window.maximize()

window = Gtk.Window()
window.show_all()
window.maximize()

Gtk.main()