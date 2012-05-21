#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright © 2012 Thomas Krug
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

# TODO
# - tooltip

import optparse
import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GdkPixbuf

global sysfs
sysfs = "/sys/devices/platform/smapi"

global iconpath
iconpath = "/usr/share/pixmaps/tp-battery-icons/"

global iconname
iconname = "/usr/share/pixmaps/tp-battery-icon.svg"

def read_sysfs(path):
    try:
        node_path = os.path.join(sysfs, bat, path)
        with open(node_path, "r") as node:
            result = node.readline()
    except IOError:
        print("error reading from", node_path)
        return
    return result

def write_sysfs(path, value):
    try:
        node_path = os.path.join(sysfs, bat, path)
        with open(node_path, "w+") as node:
            node.write(str(value))
    except IOError:
        print("error writing to", node_path)
        return

class Control():

    def set_threshold_start(self, thresh):
        if 0 <= thresh <= 100:
            if debug:
                print("setting start charge threshold to", thresh)
            else:
                write_sysfs("start_charge_thresh", thresh)

    def set_threshold_stop(self, thresh):
        if 0 <= thresh <= 100:
            if debug:
                print("setting stop charge threshold to", thresh)
            else:
                write_sysfs("stop_charge_thresh", thresh)

    def start_charge(self, widget=None):
        if debug:
            print("starting charge")
        else:
            cur = self.get_percent()
            self.set_threshold_start(cur + 1)

    def start_cycle(self, widget=None):
        if debug:
            print("starting cycle")
        else:
            write_sysfs("force_discharge", 1)

    def get_threshold_start(self):
        thresh = read_sysfs("start_charge_thresh")
        return int(thresh)

    def get_threshold_stop(self):
        thresh = read_sysfs("stop_charge_thresh")
        return int(thresh)

    def get_state(self):
        """
        idle, discharging, charging, none
        """
        state = read_sysfs("state")
        return state.rstrip()

    def get_percent(self):
        percent = read_sysfs("remaining_percent")
        return int(percent)

    def get_time_running(self):
        time = read_sysfs("remaining_running_time")
        try:
            hh = str(int(time) / 60).split('.')[0]
            mm = str(int(time) % 60).split('.')[0].zfill(2)
            return hh + ":" + mm
        except ValueError:
            return "--:--"

    def get_time_charging(self):
        time = read_sysfs("remaining_charging_time")
        try:
            hh = str(int(time) / 60).split('.')[0]
            mm = str(int(time) % 60).split('.')[0].zfill(2)
            return hh + ":" + mm
        except ValueError:
            return "--:--"

    def check_installed(self):
        present = read_sysfs("installed")
        return int(present) == 1

class TrayIcon():

    icon = None
    menu = None

    def __init__(self):
        self.icon = Gtk.StatusIcon()
        #self.icon.connect("activate", self.on_popup_menu)
        self.icon.connect("popup-menu", self.on_popup_menu)

    def get_menu(self):
        self.menu = Gtk.Menu()

        state = ctrl.get_state()

        if state == "none":
            title = bat + " not installed"
        else:
            title = bat + " " + str(ctrl.get_percent()) + "% " + state

        if state == "charging":
            title += " " + ctrl.get_time_charging()
        if state == "discharging":
            title += " " + ctrl.get_time_running()

        header = Gtk.MenuItem(title)
        # TODO implement detail dialog
        #header.connect("activate", )
        self.menu.append(header)

        sep1 = Gtk.SeparatorMenuItem()
        self.menu.append(sep1)

        if state != "none":

            start = Gtk.MenuItem("Start Threshold " + str(ctrl.get_threshold_start()) + "%")
            start.connect("activate", self.show_input_dialog,
                          "Start Threshold", "Set new <b>start</b> threshold:",
                          self.set_threshold_start, iconpath + "empty.svg", str(ctrl.get_threshold_start()))
            self.menu.append(start)

            stop = Gtk.MenuItem("Stop Threshold " + str(ctrl.get_threshold_stop()) + "%")
            stop.connect("activate", self.show_input_dialog,
                         "Stop Threshold", "Set new <b>stop</b> threshold:",
                         self.set_threshold_stop, iconpath + "full.svg", str(ctrl.get_threshold_stop()))
            self.menu.append(stop)

            sep2 = Gtk.SeparatorMenuItem()
            self.menu.append(sep2)

            charge = Gtk.MenuItem("Start Charge")
            charge.connect("activate", self.show_confirmation_dialog,
                           "Confirm Charge", "Start charging?",
                           ctrl.start_charge, iconpath + "charging-empty.svg")
            self.menu.append(charge)

            cycle = Gtk.MenuItem("Start Cycle")
            cycle.connect("activate", self.show_confirmation_dialog,
                          "Confirm Cycle", "Start cycling?",
                          ctrl.start_cycle, iconpath + "charging-full.svg")
            self.menu.append(cycle)

            sep3 = Gtk.SeparatorMenuItem()
            self.menu.append(sep3)

        about = Gtk.MenuItem("About")
        about.connect("activate", self.show_about_dialog)
        self.menu.append(about)

        quit = Gtk.MenuItem("Quit")
        quit.connect("activate", self.quit)
        self.menu.append(quit)

    def quit(self, widget):
        loop.quit()

    def on_popup_menu(self, icon, button=3, time=0):
        self.get_menu()
        self.menu.show_all()
        self.menu.popup(None, None, None, None, button, time)

    def update(self):
        foo = iconpath

        state = ctrl.get_state()

        if state == "none":
            icon.icon.set_from_file(foo + "missing.svg")
            return

        if state == "charging":
            foo += "charging-"

        cur = ctrl.get_percent()
        if   cur > 80:
            foo += "full.svg"
        elif cur > 40:
            foo += "good.svg"
        elif cur > 20:
            foo += "low.svg"
        else:
            foo += "empty.svg"

        icon.icon.set_from_file(foo)


        if state == "none":
            title = bat + " not installed"
        else:
            title = bat + " " + str(ctrl.get_percent()) + "% " + state

        if state == "charging":
            title += " " + ctrl.get_time_charging()
        if state == "discharging":
            title += " " + ctrl.get_time_running()

        icon.icon.set_tooltip_text(title)

    def set_threshold_start(self, widget, foo):
        thresh = int(widget.get_text())
        if 0 <= thresh <= 100:
            ctrl.set_threshold_start(thresh)

    def set_threshold_stop(self, widget, foo):
        thresh = int(widget.get_text())
        if 0 <= thresh <= 100:
            ctrl.set_threshold_stop(thresh)

    def respond(self, entry, dialog, response):
        dialog.response(response)

    def show_input_dialog(self, widget, title, question, function, imagename, answer=""):
        dialog = Gtk.Dialog(title, None, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        #dialog = Gtk.Dialog(title, None, 0)
        dialog.set_icon_from_file(iconname)

        hbox = Gtk.HBox()
        dialog.vbox.pack_start(hbox, True, True, 0)

        image = Gtk.Image()
        image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(imagename, 50, 50))
        image.set_padding(10, 10)
        hbox.pack_start(image, False, False, 0)

        vbox = Gtk.VBox()
        hbox.pack_start(vbox, True, True, 0)

        label = Gtk.Label()
        label.set_markup(question)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_padding(10, 10)
        vbox.pack_start(label, False, False, 0)

        dialog_entry = Gtk.Entry()
        dialog_entry.connect("activate", self.respond, dialog, Gtk.ResponseType.OK)
        if answer:
            dialog_entry.set_text(answer)
        vbox.pack_start(dialog_entry, False, False, 0)
        dialog.show_all()

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            function(dialog_entry)

        dialog.destroy()

    def show_confirmation_dialog(self, widget, title, question, function, imagename):
        dialog = Gtk.Dialog(title, None, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_icon_from_file(iconname)

        hbox = Gtk.HBox()
        dialog.vbox.pack_start(hbox, True, True, 0)

        image = Gtk.Image()
        image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(imagename, 50, 50))
        image.set_padding(10, 10)
        hbox.pack_start(image, False, False, 0)

        label = Gtk.Label()
        label.set_markup(question)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_padding(10, 10)
        hbox.add(label)

        dialog.show_all()

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            function()

        dialog.destroy()

    def show_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()

        about_dialog.set_program_name("TP Battery Icon")
        about_dialog.set_version("0.1")
        about_dialog.set_comments("A simple yet useful tray icon, using tp_smapi.")
        about_dialog.set_copyright("Copyright © 2012 Thomas Krug")
        about_dialog.set_website("https://github.com/phragment/tp-battery-icon")
        about_dialog.set_website_label("github.com/phragment/tp-battery-icon")
        about_dialog.set_icon_from_file(iconname)

        about_dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_size(iconname, 200, 200))

        about_dialog.run()
        about_dialog.destroy()

def timer():
    icon.update()
    GObject.timeout_add_seconds(10, timer)

if __name__ == "__main__":
    global loop
    global icon
    global ctrl
    global debug
    global bat

    parser = optparse.OptionParser()

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="TODO")
    parser.add_option("-b", "--battery",
                      action="store", dest="bat", default="BAT0",
                      help="TODO")

    (options, args) = parser.parse_args()

    debug = options.debug
    bat = options.bat

    try:
        loop = GObject.MainLoop(None, False)

        ctrl = Control()
        icon = TrayIcon()

        timer()

        loop.run()

    except KeyboardInterrupt:
        loop.quit()
