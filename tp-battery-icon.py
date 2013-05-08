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

import sys
import optparse
import os
import subprocess
import signal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GdkPixbuf

#-------------------------------------------------------------------------------

class ControlTPsmapi():

    def __init__(self):

        self.name = "tp_smapi"

        self.bat = "BAT" + str(bat - 1)
        self.sysfs = "/sys/devices/platform/smapi"

        # probe
        try:
            result = self.read_sysfs("installed")
        except Exception:
            raise Exception("SMAPI not supported")


    def read_sysfs(self, path):
        try:
            node_path = os.path.join(self.sysfs, self.bat, path)
            with open(node_path, "r") as node:
                result = node.readline()
            return result
        except IOError:
            raise Exception("error reading from", node_path)

    def write_sysfs(self, path, value):
        try:
            node_path = os.path.join(self.sysfs, self.bat, path)
            with open(node_path, "w+") as node:
                node.write(str(value))
        except IOError:
            raise Exception("error writing to", node_path)


    def get_state(self):
        """return values: idle, discharging, charging, none"""
        state = self.read_sysfs("state")
        return state.rstrip()

    def get_percentage(self):
        percent = self.read_sysfs("remaining_percent")
        return int(percent)

    def get_time_running(self):
        time = self.read_sysfs("remaining_running_time")
        return int(time)

    def get_time_charging(self):
        time = self.read_sysfs("remaining_charging_time")
        return int(time)

    def get_start_threshold(self):
        thresh = self.read_sysfs("start_charge_thresh")
        return int(thresh)

    def get_stop_threshold(self):
        thresh = self.read_sysfs("stop_charge_thresh")
        return int(thresh)

    def set_start_threshold(self, threshold):
        self.write_sysfs("start_charge_thresh", threshold)

    def set_stop_threshold(self, threshold):
        self.write_sysfs("stop_charge_thresh", threshold)

    def start_charging(self):
        cur = self.get_percentage()
        self.set_start_threshold(cur + 1)

    def start_cycle(self):
        self.write_sysfs("force_discharge", 1)

#-------------------------------------------------------------------------------

class ControlTPacpi():

    def __init__(self):

        self.name = "acpi_call"

        self.bat = bat

        # probe: read force discharge
        param = hex(self.bat)
        result = self.acpi_call("\_SB.PCI0.LPC.EC.HKEY.BDSG " + param)
        if (result == "Error: AE_NOT_FOUND"):
            raise Exception("unsupported ThinkPad model")

        self.acpi = ControlACPI()

    def acpi_call(self, value):

        try:
            if (value):
                call = open("/proc/acpi/call", "w+")

                call.write(str(value))
                call.close()


            call = open("/proc/acpi/call", "r")

            result = call.readline()
            call.close()

            return result

        except OSError:
            raise Exception("couldn't open /proc/acpi/call, check if acpi_call loaded")
        except IOError:
            raise Exception("couldn't read from /proc/acpi/call, check permissions")

    def get_state(self):
        return self.acpi.get_state()

    def get_percentage(self):
        return self.acpi.get_percentage()

    def get_time_running(self):
        return self.acpi.get_time_running()

    def get_time_charging(self):
        return self.acpi.get_time_charging()

    def get_start_threshold(self):
        param = hex(self.bat)
        result = self.acpi_call("\_SB.PCI0.LPC.EC.HKEY.BCTG " + param)
        return int(result, 16) - (3 * 256)

    def get_stop_threshold(self):
        param = hex(self.bat)
        result = self.acpi_call("\_SB.PCI0.LPC.EC.HKEY.BCSG " + param)
        ret = int(result, 16) - (3 * 256)
        if ret == 0:
            ret = 100
        return ret

    def set_start_threshold(self, threshold):
        param = hex(self.bat * 256 + threshold)
        self.acpi_call("\_SB.PCI0.LPC.EC.HKEY.BCCS " + param)

    def set_stop_threshold(self, threshold):
        if threshold == 100:
            threshold = 0
        param = hex(self.bat * 256 + threshold)
        self.acpi_call("\_SB.PCI0.LPC.EC.HKEY.BCSS " + param)

    def start_charging(self):
        cur = self.get_percentage()
        self.set_start_threshold(cur + 1)

    def start_cycle(self):
        param = hex(self.bat)
        self.acpi_call("\_SB.PCI0.LPC.EC.HKEY.BDSG " + param)

#-------------------------------------------------------------------------------

class ControlACPI():

    def __init__(self):

        self.name = "ACPI"

        self.bat = "BAT" + str(bat - 1)
        self.sysfs = "/sys/class/power_supply"

        # catch all


    def read_sysfs(self, path):
        try:
            node_path = os.path.join(self.sysfs, self.bat, path)
            with open(node_path, "r") as node:
                result = node.readline()
            return result
        except IOError:
            raise Exception("error reading from", node_path)


    def get_state(self):
        """return values: Discharging, Charging, Unknown"""
        try:
            state = self.read_sysfs("status")
        except Exception:
            state = "none"

        state = state.lower()

        if state == "unknown":
            state = "idle"

        return state.rstrip()

    def get_percentage(self):
        try:
            percent = self.read_sysfs("capacity")
        except Exception:
            percent = int(self.read_sysfs("energy_full")) / int(self.read_sysfs("energy_now")) * 100.0
        return int(percent)

    def get_time_running(self):
        try:
            current = int(self.read_sysfs("power_now"))
        except Exception:
            current = int(self.read_sysfs("current_now"))

        try:
            charge = int(self.read_sysfs("energy_now"))
        except Exception:
            charge = int(self.read_sysfs("charge_now"))

        if current == 0:
            return 0

        time = charge / current * 60

        return int(time)

    def get_time_charging(self):
        try:
            full = int(self.read_sysfs("energy_full"))
        except Exception:
            full = int(self.read_sysfs("charge_full"))

        try:
            now = int(self.read_sysfs("energy_now"))
        except Exception:
            now = int(self.read_sysfs("charge_now"))

        try:
            current = int(self.read_sysfs("power_now"))
        except Exception:
            current = int(self.read_sysfs("current_now"))

        if current == 0:
            return 0

        missing = full - now
        time = missing / current * 60

        return int(time)

#-------------------------------------------------------------------------------

class TrayIcon():

    def __init__(self):
        self.icon = None
        self.menu = None

        self.iconpath = "/usr/share/pixmaps/tp-battery-icons/"
        self.iconname = "/usr/share/pixmaps/tp-battery-icon.svg"

        self.icon = Gtk.StatusIcon()
        self.icon.connect("popup-menu", self.on_popup_menu)

    def get_menu(self):
        self.menu = Gtk.Menu()

        state = ctrl.get_state()

        if state == "none":
            title = "Battery " + str(bat) + " not installed"
        else:
            title = "Battery " + str(bat) + " at " + str(ctrl.get_percentage()) + "%"

        header = Gtk.MenuItem(title)
        header.connect("activate", self.show_detail_dialog)
        self.menu.append(header)

        subtitle = ""
        if state == "charging":
            subtitle += state + " " + self.format_time(ctrl.get_time_charging())
        if state == "discharging":
            subtitle += state + " " + self.format_time(ctrl.get_time_running())

        if subtitle:
            subheader = Gtk.MenuItem(subtitle)
            #subheader.connect("activate", )
            self.menu.append(subheader)

        sep1 = Gtk.SeparatorMenuItem()
        self.menu.append(sep1)

        if state != "none":

            try:
                start = Gtk.MenuItem("Start Threshold " + str(ctrl.get_start_threshold()) + "%")
                start.connect("activate", self.show_input_dialog,
                              "Start Threshold", "Set new <b>start</b> threshold:",
                              self.set_threshold_start, self.iconpath + "empty.svg",
                              str(ctrl.get_start_threshold()))
                self.menu.append(start)


                stop = Gtk.MenuItem("Stop Threshold " + str(ctrl.get_stop_threshold()) + "%")
                stop.connect("activate", self.show_input_dialog,
                             "Stop Threshold", "Set new <b>stop</b> threshold:",
                             self.set_threshold_stop, self.iconpath + "full.svg",
                             str(ctrl.get_stop_threshold()))
                self.menu.append(stop)

                sep2 = Gtk.SeparatorMenuItem()
                self.menu.append(sep2)
            except AttributeError:
                pass

            try:
                charge = Gtk.MenuItem("Start Charge")
                charge.connect("activate", self.show_confirmation_dialog,
                               "Confirm Charge", "Start charging?",
                               ctrl.start_charging, self.iconpath + "charging-empty.svg")
                self.menu.append(charge)


                cycle = Gtk.MenuItem("Start Cycle")
                cycle.connect("activate", self.show_confirmation_dialog,
                              "Confirm Cycle", "Start cycling?",
                              ctrl.start_cycle, self.iconpath + "charging-full.svg")
                self.menu.append(cycle)

                sep3 = Gtk.SeparatorMenuItem()
                self.menu.append(sep3)
            except AttributeError:
                pass

        about = Gtk.MenuItem("About")
        about.connect("activate", self.show_about_dialog)
        self.menu.append(about)

        quit = Gtk.MenuItem("Quit")
        quit.connect("activate", self.quit)
        self.menu.append(quit)

    def quit(self, widget):
        Gtk.main_quit()

    def on_popup_menu(self, icon, button=3, time=0):
        self.get_menu()
        self.menu.show_all()
        self.menu.popup(None, None, None, None, button, time)

    def update(self):
        foo = self.iconpath

        state = ctrl.get_state()

        if state == "none":
            icon.icon.set_from_file(foo + "missing.svg")
            return

        if state == "charging":
            foo += "charging-"

        cur = ctrl.get_percentage()
        if   cur > 60:
            foo += "full.svg"
        elif cur > 40:
            foo += "good.svg"
        elif cur > 20:
            foo += "low.svg"
        else:
            foo += "empty.svg"

        icon.icon.set_from_file(foo)


        if state == "none":
            title = "Battery " + str(bat) + " not installed"
        else:
            title = "Battery " + str(bat) + " at " + str(ctrl.get_percentage()) + "% " + state

        # TODO
        if state == "charging":
            title += " " + self.format_time(ctrl.get_time_charging())
        if state == "discharging":
            title += " " + self.format_time(ctrl.get_time_running())

        icon.icon.set_tooltip_text(title)

    def set_threshold_start(self, widget):
        try:
            thresh = int(widget.get_text())
            if 1 <= thresh <= 100:
                ctrl.set_start_threshold(thresh)
        except ValueError:
            # TODO message dialog
            print("Invalid value in dialog!")

    def set_threshold_stop(self, widget):
        try:
            thresh = int(widget.get_text())
            if 1 <= thresh <= 100:
                ctrl.set_stop_threshold(thresh)
        except ValueError:
            # TODO message dialog
            print("Invalid value in dialog!")

    def respond(self, entry, dialog, response):
        dialog.response(response)

    def show_input_dialog(self, widget, title, question, function, imagename, answer=""):
        dialog = Gtk.Dialog(title, None, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_icon_from_file(self.iconname)

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
        dialog.set_icon_from_file(self.iconname)

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

    def show_detail_dialog(self, widget):
        print("hui")

    def show_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()

        about_dialog.set_program_name("ThinkPad Battery Icon")
        about_dialog.set_version("0.2")
        about_dialog.set_comments("A simple yet powerful tray icon, using: " + ctrl.name)
        about_dialog.set_copyright("Copyright © 2012 Thomas Krug")
        about_dialog.set_website("https://github.com/phragment/tp-battery-icon")
        about_dialog.set_website_label("github.com/phragment/tp-battery-icon")
        about_dialog.set_icon_from_file(self.iconname)

        about_dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_size(self.iconname, 200, 200))

        about_dialog.run()
        about_dialog.destroy()

    def format_time(self, time):
        try:
            hh = str(time / 60).split('.')[0]
            mm = str(time % 60).split('.')[0].zfill(2)
            return hh + ":" + mm
        except ValueError:
            return "--:--"

#-------------------------------------------------------------------------------

def timer():
    icon.update()
    GObject.timeout_add_seconds(10, timer)

def signal_handler(signum, frame):
    Gtk.main_quit()

if __name__ == "__main__":
    global icon
    global ctrl
    global debug
    global bat
    global acpi

    parser = optparse.OptionParser()
    parser.add_option("-b", "--battery", action="store",
                      dest="bat", default="1",
                      help="set which battery to observe.")
    (options, args) = parser.parse_args()

    bat = int(options.bat)

    if bat < 1 or bat > 2:
        print("Choose Battery 1 or 2.")
        sys.exit(1)

    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    ctrls = [ControlTPacpi, ControlTPsmapi, ControlACPI]

    ctrl = None
    for test_ctrl in ctrls:
        if not ctrl:
            try:
                ctrl = test_ctrl()
            except Exception:
                ctrl = None

    if not ctrl:
        print("no module found")
        sys.exit(1)

    icon = TrayIcon()

    timer()

    Gtk.main()

