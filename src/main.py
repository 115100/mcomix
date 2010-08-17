"""main.py - Main window."""

import sys
import os
import shutil
import threading

import gtk
import gobject

import constants
import cursor
import encoding
import enhance
import event
import filehandler
import image
import lens
import preferences
from preferences import prefs
import ui
import slideshow
import status
import thumbbar


class MainWindow(gtk.Window):

    """The Comix main window, is created at start and terminates the
    program when closed.
    """

    def __init__(self, fullscreen=False, show_library=False, open_path=None,
            open_page=1):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)

        # ----------------------------------------------------------------
        # Attributes
        # ----------------------------------------------------------------
        self.is_fullscreen = False
        self.is_double_page = False
        self.is_manga_mode = False
        self.is_virtual_double_page = False # I.e. a wide image is displayed
        self.zoom_mode = preferences.ZOOM_MODE_BEST
        self.width = None
        self.height = None

        self._manual_zoom = 100 # In percent of original image size
        self._waiting_for_redraw = False

        self.file_handler = filehandler.FileHandler(self)
        self.thumbnailsidebar = thumbbar.ThumbnailSidebar(self)
        self.statusbar = status.Statusbar()
        self.slideshow = slideshow.Slideshow(self)
        self.cursor_handler = cursor.CursorHandler(self)
        self.enhancer = enhance.ImageEnhancer(self)
        self.glass = lens.MagnifyingGlass(self)
        self.ui_manager = ui.MainUI(self)
        self.menubar = self.ui_manager.get_widget('/Menu')
        self.toolbar = self.ui_manager.get_widget('/Tool')
        self.popup = self.ui_manager.get_widget('/Popup')
        self.actiongroup = self.ui_manager.get_action_groups()[0]
        self.left_image = gtk.Image()
        self.right_image = gtk.Image()

        self._image_box = gtk.HBox(False, 2)
        self._main_layout = gtk.Layout()
        self._event_handler = event.EventHandler(self)
        self._vadjust = self._main_layout.get_vadjustment()
        self._hadjust = self._main_layout.get_hadjustment()
        self._vscroll = gtk.VScrollbar(self._vadjust)
        self._hscroll = gtk.HScrollbar(self._hadjust)

        # ----------------------------------------------------------------
        # Setup
        # ----------------------------------------------------------------
        self.set_title('Comix')
        self.set_size_request(300, 300)  # Avoid making the window *too* small
        self.resize(prefs['window width'], prefs['window height'])

        # This is a hack to get the focus away from the toolbar so that
        # we don't activate it with space or some other key (alternative?)
        self.toolbar.set_focus_child(
            self.ui_manager.get_widget('/Tool/expander'))
        self.toolbar.set_style(gtk.TOOLBAR_ICONS)
        self.toolbar.set_icon_size(gtk.ICON_SIZE_LARGE_TOOLBAR)

        self._image_box.add(self.left_image)
        self._image_box.add(self.right_image)
        self._image_box.show_all()

        self._main_layout.put(self._image_box, 0, 0)
        self.set_bg_colour(prefs['bg colour'])

        self._vadjust.step_increment = 15
        self._vadjust.page_increment = 1
        self._hadjust.step_increment = 15
        self._hadjust.page_increment = 1

        table = gtk.Table(2, 2, False)
        table.attach(self.thumbnailsidebar, 0, 1, 2, 5, gtk.FILL,
            gtk.FILL|gtk.EXPAND, 0, 0)
        table.attach(self._main_layout, 1, 2, 2, 3, gtk.FILL|gtk.EXPAND,
            gtk.FILL|gtk.EXPAND, 0, 0)
        table.attach(self._vscroll, 2, 3, 2, 3, gtk.FILL|gtk.SHRINK,
            gtk.FILL|gtk.SHRINK, 0, 0)
        table.attach(self._hscroll, 1, 2, 4, 5, gtk.FILL|gtk.SHRINK,
            gtk.FILL, 0, 0)
        table.attach(self.menubar, 0, 3, 0, 1, gtk.FILL|gtk.SHRINK,
            gtk.FILL, 0, 0)
        table.attach(self.toolbar, 0, 3, 1, 2, gtk.FILL|gtk.SHRINK,
            gtk.FILL, 0, 0)
        table.attach(self.statusbar, 0, 3, 5, 6, gtk.FILL|gtk.SHRINK,
            gtk.FILL, 0, 0)

        if prefs['default double page']:
            self.actiongroup.get_action('double_page').activate()
        if prefs['default fullscreen'] or fullscreen:
            self.actiongroup.get_action('fullscreen').activate()
        if prefs['default manga mode']:
            self.actiongroup.get_action('manga_mode').activate()
        if prefs['default zoom mode'] == preferences.ZOOM_MODE_BEST:
            self.actiongroup.get_action('best_fit_mode').activate()
        elif prefs['default zoom mode'] == preferences.ZOOM_MODE_WIDTH:
            self.actiongroup.get_action('fit_width_mode').activate()
        elif prefs['default zoom mode'] == preferences.ZOOM_MODE_HEIGHT:
            self.actiongroup.get_action('fit_height_mode').activate()
        elif prefs['default zoom mode'] == preferences.ZOOM_MODE_MANUAL:
            # This little ugly hack is to get the activate call on
            # 'fit_manual_mode' to actually create an event (and callback).
            # Since manual mode is the default selected radio button action
            # it won't send an event if we activate it when it is already
            # the selected one.
            self.actiongroup.get_action('best_fit_mode').activate()
            self.actiongroup.get_action('fit_manual_mode').activate()
        if prefs['show toolbar']:
            prefs['show toolbar'] = False
            self.actiongroup.get_action('toolbar').activate()
        if prefs['show menubar']:
            prefs['show menubar'] = False
            self.actiongroup.get_action('menubar').activate()
        if prefs['show statusbar']:
            prefs['show statusbar'] = False
            self.actiongroup.get_action('statusbar').activate()
        if prefs['show scrollbar']:
            prefs['show scrollbar'] = False
            self.actiongroup.get_action('scrollbar').activate()
        if prefs['show thumbnails']:
            prefs['show thumbnails'] = False
            self.actiongroup.get_action('thumbnails').activate()
        if prefs['hide all']:
            prefs['hide all'] = False
            self.actiongroup.get_action('hide all').activate()
        if prefs['keep transformation']:
            prefs['keep transformation'] = False
            self.actiongroup.get_action('keep_transformation').activate()
        else:
            prefs['rotation'] = 0
            prefs['vertical flip'] = False
            prefs['horizontal flip'] = False

        self.add(table)
        table.show()
        self._main_layout.show()
        self._display_active_widgets()

        self._main_layout.set_events(gtk.gdk.BUTTON1_MOTION_MASK |
                                     gtk.gdk.BUTTON2_MOTION_MASK |
                                     gtk.gdk.BUTTON_PRESS_MASK |
                                     gtk.gdk.BUTTON_RELEASE_MASK |
                                     gtk.gdk.POINTER_MOTION_MASK)
        self._main_layout.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                                        [('text/uri-list', 0, 0)],
                                        gtk.gdk.ACTION_COPY |
                                        gtk.gdk.ACTION_MOVE)

        self.connect('delete_event', self.terminate_program)
        self.connect('key_press_event', self._event_handler.key_press_event)
        self.connect('configure_event', self._event_handler.resize_event)
        self._main_layout.connect('button_release_event',
            self._event_handler.mouse_release_event)
        self._main_layout.connect('scroll_event',
            self._event_handler.scroll_wheel_event)
        self._main_layout.connect('button_press_event',
            self._event_handler.mouse_press_event)
        self._main_layout.connect('motion_notify_event',
            self._event_handler.mouse_move_event)
        self._main_layout.connect('drag_data_received',
            self._event_handler.drag_n_drop_event)

        self.ui_manager.set_sensitivities()
        self.show()
        if open_path is not None:
            self.file_handler.open_file(open_path, open_page)
        if show_library:
            self.actiongroup.get_action('library').activate()

    def draw_image(self, at_bottom=False, scroll=True):
        """Draw the current page(s) and update the titlebar and statusbar.
        """
        if not self._waiting_for_redraw: # Don't stack up redraws.
            self._waiting_for_redraw = True
            gobject.idle_add(self._draw_image, at_bottom, scroll,
                priority=gobject.PRIORITY_HIGH_IDLE)

    def _draw_image(self, at_bottom, scroll):
        self._waiting_for_redraw = False
        self._display_active_widgets()
        if not self.file_handler.file_loaded:
            return False
        area_width, area_height = self.get_visible_area_size()
        if self.zoom_mode == preferences.ZOOM_MODE_HEIGHT:
            scaled_width = -1
        else:
            scaled_width = area_width
        if self.zoom_mode == preferences.ZOOM_MODE_WIDTH:
            scaled_height = -1
        else:
            scaled_height = area_height
        scale_up = prefs['stretch']
        self.is_virtual_double_page = \
            self.file_handler.get_virtual_double_page()

        if self.displayed_double():
            left_pixbuf, right_pixbuf = self.file_handler.get_pixbufs()
            if self.is_manga_mode:
                right_pixbuf, left_pixbuf = left_pixbuf, right_pixbuf
            left_unscaled_x = left_pixbuf.get_width()
            left_unscaled_y = left_pixbuf.get_height()
            right_unscaled_x = right_pixbuf.get_width()
            right_unscaled_y = right_pixbuf.get_height()

            left_rotation = prefs['rotation']
            right_rotation = prefs['rotation']
            if prefs['auto rotate from exif']:
                left_rotation += image.get_implied_rotation(left_pixbuf)
                left_rotation = left_rotation % 360
                right_rotation += image.get_implied_rotation(right_pixbuf)
                right_rotation = right_rotation % 360

            if self.zoom_mode == preferences.ZOOM_MODE_MANUAL:
                if left_rotation in (90, 270):
                    total_width = left_unscaled_y
                    total_height = left_unscaled_x
                else:
                    total_width = left_unscaled_x
                    total_height = left_unscaled_y
                if right_rotation in (90, 270):
                    total_width += right_unscaled_y
                    total_height += right_unscaled_x
                else:
                    total_width += right_unscaled_x
                    total_height += right_unscaled_y
                total_width += 2 # For the 2 px gap between images. 
                scaled_width = int(self._manual_zoom * total_width / 100)
                scaled_height = int(self._manual_zoom * total_height / 100)
                scale_up = True

            left_pixbuf, right_pixbuf = image.fit_2_in_rectangle(
                left_pixbuf, right_pixbuf, scaled_width, scaled_height,
                scale_up=scale_up, rotation1=left_rotation,
                rotation2=right_rotation)
            if prefs['horizontal flip']:
                left_pixbuf = left_pixbuf.flip(horizontal=True)
                right_pixbuf = right_pixbuf.flip(horizontal=True)
            if prefs['vertical flip']:
                left_pixbuf = left_pixbuf.flip(horizontal=False)
                right_pixbuf = right_pixbuf.flip(horizontal=False)
            left_pixbuf = self.enhancer.enhance(left_pixbuf)
            right_pixbuf = self.enhancer.enhance(right_pixbuf)

            self.left_image.set_from_pixbuf(left_pixbuf)
            self.right_image.set_from_pixbuf(right_pixbuf)
            x_padding = (area_width - left_pixbuf.get_width() -
                right_pixbuf.get_width()) / 2
            y_padding = (area_height - max(left_pixbuf.get_height(),
                right_pixbuf.get_height())) / 2
            
            if left_rotation in (90, 270):
                left_scale_percent = (100.0 * left_pixbuf.get_width() /
                    left_unscaled_y)
            else:
                left_scale_percent = (100.0 * left_pixbuf.get_width() /
                    left_unscaled_x)
            if right_rotation in (90, 270):
                right_scale_percent = (100.0 * right_pixbuf.get_width() /
                    right_unscaled_y)
            else:
                right_scale_percent = (100.0 * right_pixbuf.get_width() /
                    right_unscaled_x)
            self.statusbar.set_page_number(
                self.file_handler.get_current_page(),
                self.file_handler.get_number_of_pages(), double_page=True)
            self.statusbar.set_resolution(
                (left_unscaled_x, left_unscaled_y, left_scale_percent),
                (right_unscaled_x, right_unscaled_y, right_scale_percent))
            left_filename, right_filename = \
                self.file_handler.get_page_filename(double=True)
            if self.is_manga_mode:
                left_filename, right_filename = right_filename, left_filename
            self.statusbar.set_filename(left_filename + ', ' + right_filename)
        else:
            pixbuf = self.file_handler.get_pixbufs(single=True)
            unscaled_x = pixbuf.get_width()
            unscaled_y = pixbuf.get_height()

            rotation = prefs['rotation']
            if prefs['auto rotate from exif']:
                rotation += image.get_implied_rotation(pixbuf)
                rotation = rotation % 360

            if self.zoom_mode == preferences.ZOOM_MODE_MANUAL:
                scaled_width = int(self._manual_zoom * unscaled_x / 100)
                scaled_height = int(self._manual_zoom * unscaled_y / 100)
                if rotation in (90, 270):
                    scaled_width, scaled_height = scaled_height, scaled_width
                scale_up = True
            
            pixbuf = image.fit_in_rectangle(pixbuf, scaled_width,
                scaled_height, scale_up=scale_up, rotation=rotation)
            if prefs['horizontal flip']:
                pixbuf = pixbuf.flip(horizontal=True)
            if prefs['vertical flip']:
                pixbuf = pixbuf.flip(horizontal=False)
            pixbuf = self.enhancer.enhance(pixbuf)

            self.left_image.set_from_pixbuf(pixbuf)
            self.right_image.clear()
            x_padding = (area_width - pixbuf.get_width()) / 2
            y_padding = (area_height - pixbuf.get_height()) / 2
            
            if rotation in (90, 270):
                scale_percent = 100.0 * pixbuf.get_width() / unscaled_y
            else:
                scale_percent = 100.0 * pixbuf.get_width() / unscaled_x
            self.statusbar.set_page_number(
                self.file_handler.get_current_page(),
                self.file_handler.get_number_of_pages())
            self.statusbar.set_resolution((unscaled_x, unscaled_y,
                scale_percent))
            self.statusbar.set_filename(self.file_handler.get_page_filename())
        
        if prefs['smart bg']:
            bg_colour = image.get_most_common_edge_colour(
                self.left_image.get_pixbuf())
            self.set_bg_colour(bg_colour)

        self._image_box.window.freeze_updates()
        self._main_layout.move(self._image_box, max(0, x_padding),
            max(0, y_padding))
        self.left_image.show()
        if self.displayed_double():
            self.right_image.show()
        else:
            self.right_image.hide()
        self._main_layout.set_size(*self._image_box.size_request())
        if scroll:
            if at_bottom:
                self.scroll_to_fixed(horiz='endsecond', vert='bottom')
            else:
                self.scroll_to_fixed(horiz='startfirst', vert='top')
        self._image_box.window.thaw_updates()

        self.statusbar.set_root(self.file_handler.get_base_filename())
        self.statusbar.update()
        self.update_title()
        while gtk.events_pending():
            gtk.main_iteration(False)
        enhance.draw_histogram(self.left_image)
        self.file_handler.do_cacheing()
        self.thumbnailsidebar.load_thumbnails()
        return False

    def new_page(self, at_bottom=False):
        """Draw a *new* page correctly (as opposed to redrawing the same
        image with a new size or whatever).
        """
        if not prefs['keep transformation']:
            prefs['rotation'] = 0
            prefs['horizontal flip'] = False
            prefs['vertical flip'] = False
        self.thumbnailsidebar.update_select()
        self.draw_image(at_bottom=at_bottom)

    def next_page(self, *args):
        if self.file_handler.next_page():
            self.new_page()

    def previous_page(self, *args):
        if self.file_handler.previous_page():
            self.new_page(at_bottom=True)

    def first_page(self, *args):
        if self.file_handler.first_page():
            self.new_page()

    def last_page(self, *args):
        if self.file_handler.last_page():
            self.new_page()

    def set_page(self, num):
        if self.file_handler.set_page(num):
            self.new_page()

    def rotate_90(self, *args):
        prefs['rotation'] = (prefs['rotation'] + 90) % 360
        self.draw_image()

    def rotate_180(self, *args):
        prefs['rotation'] = (prefs['rotation'] + 180) % 360
        self.draw_image()

    def rotate_270(self, *args):
        prefs['rotation'] = (prefs['rotation'] + 270) % 360
        self.draw_image()

    def flip_horizontally(self, *args):
        prefs['horizontal flip'] = not prefs['horizontal flip']
        self.draw_image()

    def flip_vertically(self, *args):
        prefs['vertical flip'] = not prefs['vertical flip']
        self.draw_image()

    def change_double_page(self, toggleaction):
        self.is_double_page = toggleaction.get_active()
        self.draw_image()

    def change_manga_mode(self, toggleaction):
        self.is_manga_mode = toggleaction.get_active()
        self.draw_image()

    def change_fullscreen(self, toggleaction):
        self.is_fullscreen = toggleaction.get_active()
        if self.is_fullscreen:
            self.fullscreen()
            self.cursor_handler.auto_hide_on()
        else:
            self.unfullscreen()
            self.cursor_handler.auto_hide_off()

    def change_zoom_mode(self, radioaction, *args):
        old_mode = self.zoom_mode
        self.zoom_mode = radioaction.get_current_value()
        sensitive = (self.zoom_mode == preferences.ZOOM_MODE_MANUAL)
        self.actiongroup.get_action('zoom_in').set_sensitive(sensitive)
        self.actiongroup.get_action('zoom_out').set_sensitive(sensitive)
        self.actiongroup.get_action('zoom_original').set_sensitive(sensitive)
        if old_mode != self.zoom_mode:
            self.draw_image()

    def change_toolbar_visibility(self, *args):
        prefs['show toolbar'] = not prefs['show toolbar']
        self.draw_image()

    def change_menubar_visibility(self, *args):
        prefs['show menubar'] = not prefs['show menubar']
        self.draw_image()

    def change_statusbar_visibility(self, *args):
        prefs['show statusbar'] = not prefs['show statusbar']
        self.draw_image()

    def change_scrollbar_visibility(self, *args):
        prefs['show scrollbar'] = not prefs['show scrollbar']
        self.draw_image()

    def change_thumbnails_visibility(self, *args):
        prefs['show thumbnails'] = not prefs['show thumbnails']
        self.draw_image()

    def change_hide_all(self, *args):
        prefs['hide all'] = not prefs['hide all']
        sensitive = not prefs['hide all']
        self.actiongroup.get_action('toolbar').set_sensitive(sensitive)
        self.actiongroup.get_action('menubar').set_sensitive(sensitive)
        self.actiongroup.get_action('statusbar').set_sensitive(sensitive)
        self.actiongroup.get_action('scrollbar').set_sensitive(sensitive)
        self.actiongroup.get_action('thumbnails').set_sensitive(sensitive)
        self.draw_image()

    def change_keep_transformation(self, *args):
        prefs['keep transformation'] = not prefs['keep transformation']

    def manual_zoom_in(self, *args):
        new_zoom = self._manual_zoom * 1.15
        if 95 < new_zoom < 105: # To compensate for rounding errors
            new_zoom = 100
        if new_zoom > 1000:
            return
        self._manual_zoom = new_zoom
        self.draw_image()

    def manual_zoom_out(self, *args):
        new_zoom = self._manual_zoom / 1.15
        if 95 < new_zoom < 105: # To compensate for rounding errors
            new_zoom = 100
        if new_zoom < 10:
            return
        self._manual_zoom = new_zoom
        self.draw_image()

    def manual_zoom_original(self, *args):
        self._manual_zoom = 100
        self.draw_image()

    def scroll(self, x, y, bound=None):
        """Scroll <x> px horizontally and <y> px vertically. If <bound> is
        'first' or 'second', we will not scroll out of the first or second
        page respectively (dependent on manga mode). The <bound> argument
        only makes sense in double page mode.

        Return True if call resulted in new adjustment values, False
        otherwise.
        """
        old_hadjust = self._hadjust.get_value()
        old_vadjust = self._vadjust.get_value()
        visible_width, visible_height = self.get_visible_area_size()
        hadjust_upper = max(0, self._hadjust.upper - visible_width)
        vadjust_upper = max(0, self._vadjust.upper - visible_height)
        hadjust_lower = 0
        if bound is not None and self.is_manga_mode:
            bound = {'first': 'second', 'second': 'first'}[bound]
        if bound == 'first':
            hadjust_upper = max(0, hadjust_upper -
                self.right_image.size_request()[0] - 2)
        elif bound == 'second':
            hadjust_lower = self.left_image.size_request()[0] + 2
        new_hadjust = old_hadjust + x
        new_vadjust = old_vadjust + y
        new_hadjust = max(hadjust_lower, new_hadjust)
        new_vadjust = max(0, new_vadjust)
        new_hadjust = min(hadjust_upper, new_hadjust)
        new_vadjust = min(vadjust_upper, new_vadjust)
        self._vadjust.set_value(new_vadjust)
        self._hadjust.set_value(new_hadjust)
        return old_vadjust != new_vadjust or old_hadjust != new_hadjust

    def scroll_to_fixed(self, horiz=None, vert=None):
        """Scroll using one of several fixed values.

        If either <horiz> or <vert> is as below, the display is scrolled as
        follows:

        horiz: 'left'        = left end of display
               'middle'      = middle of the display
               'right'       = right end of display
               'startfirst'  = start of first page
               'endfirst'    = end of first page
               'startsecond' = start of second page
               'endsecond'   = end of second page

        vert:  'top'         = top of display
               'middle'      = middle of display
               'bottom'      = bottom of display

        What is considered "start" and "end" depends on whether we are
        using manga mode or not.

        Return True if call resulted in new adjustment values.
        """
        old_hadjust = self._hadjust.get_value()
        old_vadjust = self._vadjust.get_value()
        new_vadjust = old_vadjust
        new_hadjust = old_hadjust
        visible_width, visible_height = self.get_visible_area_size()
        vadjust_upper = self._vadjust.upper - visible_height
        hadjust_upper = self._hadjust.upper - visible_width

        if vert == 'top':
            new_vadjust = 0
        elif vert == 'middle':
            new_vadjust = vadjust_upper / 2
        elif vert == 'bottom':
            new_vadjust = vadjust_upper

        if not self.displayed_double():
            horiz = {'startsecond': 'endfirst',
                     'endsecond': 'endfirst'}.get(horiz, horiz)

        # Manga transformations.
        if self.is_manga_mode and self.displayed_double() and horiz is not None:
            horiz = {'left':        'left',
                     'middle':      'middle',
                     'right':       'right',
                     'startfirst':  'endsecond',
                     'endfirst':    'startsecond',
                     'startsecond': 'endfirst',
                     'endsecond':   'startfirst'}[horiz]
        elif self.is_manga_mode and horiz is not None:
            horiz = {'left':        'left',
                     'middle':      'middle',
                     'right':       'right',
                     'startfirst':  'endfirst',
                     'endfirst':    'startfirst'}[horiz]

        if horiz == 'left':
            new_hadjust = 0
        elif horiz == 'middle':
            new_hadjust = hadjust_upper / 2
        elif horiz == 'right':
            new_hadjust = hadjust_upper
        elif horiz == 'startfirst':
            new_hadjust = 0
        elif horiz == 'endfirst':
            if self.displayed_double():
                new_hadjust = self.left_image.size_request()[0] - visible_width
            else:
                new_hadjust = hadjust_upper
        elif horiz == 'startsecond':
            new_hadjust = self.left_image.size_request()[0] + 2
        elif horiz == 'endsecond':
            new_hadjust = hadjust_upper
        new_hadjust = max(0, new_hadjust)
        new_vadjust = max(0, new_vadjust)
        new_hadjust = min(hadjust_upper, new_hadjust)
        new_vadjust = min(vadjust_upper, new_vadjust)
        self._vadjust.set_value(new_vadjust)
        self._hadjust.set_value(new_hadjust)
        return old_vadjust != new_vadjust or old_hadjust != new_hadjust

    def is_on_first_page(self):
        """Return True if we are currently viewing the first page, i.e. if we
        are scrolled as far to the left as possible, or if only the left page
        is visible on the main layout. In manga mode it is the other way
        around.
        """
        if not self.displayed_double():
            return True
        width, height = self.get_visible_area_size()
        if self.is_manga_mode:
            return (self._hadjust.get_value() >= self._hadjust.upper - width or
                self._hadjust.get_value() > self.left_image.size_request()[0])
        else:
            return (self._hadjust.get_value() == 0 or
                self._hadjust.get_value() + width <=
                self.left_image.size_request()[0])

    def clear(self):
        """Clear the currently displayed data (i.e. "close" the file)."""
        self.left_image.clear()
        self.right_image.clear()
        self.thumbnailsidebar.clear()
        self.set_title('Comix')
        self.statusbar.set_message('')
        self.set_bg_colour(prefs['bg colour'])
        enhance.clear_histogram()

    def displayed_double(self):
        """Return True if two pages are currently displayed."""
        return (self.is_double_page and not self.is_virtual_double_page and
            self.file_handler.get_current_page() !=
            self.file_handler.get_number_of_pages())

    def get_visible_area_size(self):
        """Return a 2-tuple with the width and height of the visible part
        of the main layout area.
        """
        width, height = self.get_size()
        if not prefs['hide all'] and not (self.is_fullscreen and
          prefs['hide all in fullscreen']):
            if prefs['show toolbar']:
                height -= self.toolbar.size_request()[1]
            if prefs['show statusbar']:
                height -= self.statusbar.size_request()[1]
            if prefs['show thumbnails']:
                width -= self.thumbnailsidebar.get_width()
            if prefs['show menubar']:
                height -= self.menubar.size_request()[1]
            if prefs['show scrollbar']:
                if self.zoom_mode == preferences.ZOOM_MODE_WIDTH:
                    width -= self._vscroll.size_request()[0]
                elif self.zoom_mode == preferences.ZOOM_MODE_HEIGHT:
                    height -= self._hscroll.size_request()[1]
                elif self.zoom_mode == preferences.ZOOM_MODE_MANUAL:
                    width -= self._vscroll.size_request()[0]
                    height -= self._hscroll.size_request()[1]
        return width, height

    def get_layout_pointer_position(self):
        """Return a 2-tuple with the x and y coordinates of the pointer
        on the main layout area, relative to the layout.
        """
        x, y = self._main_layout.get_pointer()
        x += self._hadjust.get_value()
        y += self._vadjust.get_value()
        return (x, y)

    def set_cursor(self, mode):
        """Set the cursor on the main layout area to <mode>. You should
        probably use the cursor_handler instead of using this method
        directly.
        """
        self._main_layout.window.set_cursor(mode)
        return False 

    def update_title(self):
        """Set the title acording to current state."""
        if self.displayed_double():
            title = encoding.to_unicode('[%d,%d / %d]  %s - Comix' % (
                self.file_handler.get_current_page(),
                self.file_handler.get_current_page() + 1,
                self.file_handler.get_number_of_pages(),
                self.file_handler.get_pretty_current_filename()))
        else:
            title = encoding.to_unicode('[%d / %d]  %s - Comix' % (
                self.file_handler.get_current_page(),
                self.file_handler.get_number_of_pages(),
                self.file_handler.get_pretty_current_filename()))
        if self.slideshow.is_running():
            title = '[%s] %s' % (_('SLIDESHOW'), title)
        self.set_title(title)

    def set_bg_colour(self, colour):
        """Set the background colour to <colour>. Colour is a sequence in the
        format (r, g, b). Values are 16-bit.
        """
        self._main_layout.modify_bg(gtk.STATE_NORMAL,
            gtk.gdk.colormap_get_system().alloc_color(gtk.gdk.Color(
            colour[0], colour[1], colour[2]), False, True))

    def _display_active_widgets(self):
        """Hide and/or show main window widgets depending on the current
        state.
        """
        if not prefs['hide all'] and not (self.is_fullscreen and
          prefs['hide all in fullscreen']):
            if prefs['show toolbar']:
                self.toolbar.show_all()
            else:
                self.toolbar.hide_all()
            if prefs['show statusbar']:
                self.statusbar.show_all()
            else:
                self.statusbar.hide_all()
            if prefs['show menubar']:
                self.menubar.show_all()
            else:
                self.menubar.hide_all()
            if (prefs['show scrollbar'] and
              self.zoom_mode == preferences.ZOOM_MODE_WIDTH):
                self._vscroll.show_all()
                self._hscroll.hide_all()
            elif (prefs['show scrollbar'] and
              self.zoom_mode == preferences.ZOOM_MODE_HEIGHT):
                self._vscroll.hide_all()
                self._hscroll.show_all()
            elif (prefs['show scrollbar'] and
              self.zoom_mode == preferences.ZOOM_MODE_MANUAL):
                self._vscroll.show_all()
                self._hscroll.show_all()
            else:
                self._vscroll.hide_all()
                self._hscroll.hide_all()
            if prefs['show thumbnails']:
                self.thumbnailsidebar.show()
            else:
                self.thumbnailsidebar.hide()
        else:
            self.toolbar.hide_all()
            self.menubar.hide_all()
            self.statusbar.hide_all()
            self.thumbnailsidebar.hide()
            self._vscroll.hide_all()
            self._hscroll.hide_all()

    def terminate_program(self, *args):
        """Run clean-up tasks and exit the program."""
        self.hide()
        if gtk.main_level() > 0:
            gtk.main_quit()
        if prefs['auto load last file'] and self.file_handler.file_loaded:
            prefs['path to last file'] = self.file_handler.get_real_path()
            prefs['page of last file'] = self.file_handler.get_current_page()
        else:
            prefs['path to last file'] = ''
            prefs['page of last file'] = 1
        self.file_handler.cleanup()
        preferences.write_preferences_file()
        self.ui_manager.bookmarks.write_bookmarks_file()
        # This hack is to avoid Python issue #1856.
        for thread in threading.enumerate():
            if thread is not threading.currentThread():
                thread.join()
        print 'Bye!'
        sys.exit(0)
