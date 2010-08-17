"""image.py - Various image manipulations."""

import gtk
import Image
import ImageEnhance
import ImageOps
import ImageStat

from preferences import prefs


def fit_in_rectangle(src, width, height, scale_up=False, rotation=0):
    """Scale (and return) a pixbuf so that it fits in a rectangle with
    dimensions <width> x <height>. A negative <width> or <height>
    means an unbounded dimension - both cannot be negative.

    If <rotation> is 90, 180 or 270 we rotate <src> first so that the
    rotated pixbuf is fitted in the rectangle.

    Unless <scale_up> is True we don't stretch images smaller than the
    given rectangle.

    If <src> has an alpha channel it gets a checkboard background.
    """
    # "Unbounded" really means "bounded to 10000 px" - for simplicity.
    # Comix would probably choke on larger images anyway.
    if width < 0:
        width = 10000
    elif height < 0:
        height = 10000
    width = max(width, 1)
    height = max(height, 1)

    if rotation in (90, 270):
        width, height = height, width

    src_width = src.get_width()
    src_height = src.get_height()

    if not scale_up and src_width <= width and src_height <= height:
        if src.get_has_alpha():
            if prefs['checkered bg for transparent images']:
                src = src.composite_color_simple(src_width, src_height,
                    gtk.gdk.INTERP_TILES, 255, 8, 0x777777, 0x999999)
            else:
                src = src.composite_color_simple(src_width, src_height,
                    gtk.gdk.INTERP_TILES, 255, 1024, 0xFFFFFF, 0xFFFFFF)
    else:
        if float(src_width) / width > float(src_height) / height:
            height = int(max(src_height * width / src_width, 1))
        else:
            width = int(max(src_width * height / src_height, 1))

        if src.get_has_alpha():
            if prefs['checkered bg for transparent images']:
                src = src.composite_color_simple(width, height,
                    gtk.gdk.INTERP_TILES, 255, 8, 0x777777, 0x999999)
            else:
                src = src.composite_color_simple(width, height,
                    gtk.gdk.INTERP_TILES, 255, 1024, 0xFFFFFF, 0xFFFFFF)
        else:
            src = src.scale_simple(width, height, gtk.gdk.INTERP_TILES)

    if rotation == 90:
        src = src.rotate_simple(gtk.gdk.PIXBUF_ROTATE_CLOCKWISE)
    elif rotation == 180:
        src = src.rotate_simple(gtk.gdk.PIXBUF_ROTATE_UPSIDEDOWN)
    elif rotation == 270:
        src = src.rotate_simple(gtk.gdk.PIXBUF_ROTATE_COUNTERCLOCKWISE)
    return src


def fit_2_in_rectangle(src1, src2, width, height, scale_up=False,
  rotation1=0, rotation2=0):
    """Scale two pixbufs so that they fit together (side-by-side) into a
    rectangle with dimensions <width> x <height>, with a 2 px gap.
    If one pixbuf does not use all of its allotted space, the other one
    is given it, so that the pixbufs are not necessarily scaled to the
    same percentage.

    The pixbufs are rotated according to the angles in <rotation1> and
    <rotation2> before they are scaled.

    See fit_in_rectangle() for more info on the parameters.
    """
    # "Unbounded" really means "bounded to 10000 px" - for simplicity.
    # Comix would probably choke on larger images anyway.
    if width < 0:
        width = 10000
    elif height < 0:
        height = 10000

    width -= 2              # We got a 2 px gap between images
    width = max(width, 2)   # We need at least 1 px per image
    height = max(height, 1)
    
    src1_width = src1.get_width()
    src1_height = src1.get_height()
    src2_width = src2.get_width()
    src2_height = src2.get_height()
    if rotation1 in (90, 270):
        src1_width, src1_height = src1_height, src1_width
    if rotation2 in (90, 270):
        src2_width, src2_height = src2_height, src2_width

    total_width = src1_width + src2_width
    alloc_width_src1 = max(src1_width * width / total_width, 1)
    alloc_width_src2 = max(src2_width * width / total_width, 1)
    needed_width_src1 = round(src1_width *
        min(height / float(src1_height), alloc_width_src1 / float(src1_width)))
    needed_width_src2 = round(src2_width *
        min(height / float(src2_height), alloc_width_src2 / float(src2_width)))
    if needed_width_src1 < alloc_width_src1:
        alloc_width_src2 += alloc_width_src1 - needed_width_src1
    elif needed_width_src1 >= alloc_width_src1:
        alloc_width_src1 += alloc_width_src2 - needed_width_src2

    return (fit_in_rectangle(src1, int(alloc_width_src1), height,
                             scale_up, rotation1),
            fit_in_rectangle(src2, int(alloc_width_src2), height,
                             scale_up, rotation2))


def add_border(pixbuf, thickness, colour=0x000000FF):
    """Return a pixbuf from <pixbuf> with a <thickness> px border of
    <colour> added.
    """
    canvas = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8,
        pixbuf.get_width() + thickness * 2,
        pixbuf.get_height() + thickness * 2)
    canvas.fill(colour)
    pixbuf.copy_area(0, 0, pixbuf.get_width(), pixbuf.get_height(),
        canvas, thickness, thickness)
    return canvas


def get_most_common_edge_colour(pixbuf):
    """Return the most commonly occurring pixel value along the four edges
    of <pixbuf>. The return value is a sequence, (r, g, b), with 16 bit
    values.

    Note: This could be done more cleanly with subpixbuf(), but that
    doesn't work as expected together with get_pixels().
    """
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    top_edge = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, width, 1)
    bottom_edge = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, width, 1)
    left_edge = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 1, height)
    right_edge = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 1, height)
    pixbuf.copy_area(0, 0, width, 1, top_edge, 0, 0)
    pixbuf.copy_area(0, height - 1, width, 1, bottom_edge, 0, 0)
    pixbuf.copy_area(0, 0, 1, height, left_edge, 0, 0)
    pixbuf.copy_area(width - 1, 0, 1, height, right_edge, 0, 0)
    
    colour_count = {}
    for edge in (top_edge, bottom_edge, left_edge, right_edge):
        im = pixbuf_to_pil(edge)
        for count, colour in im.getcolors(im.size[0] * im.size[1]):
            colour_count[colour] = colour_count.setdefault(colour, 0) + count
    max_count = 0
    most_common_colour = None
    for colour, count in colour_count.iteritems():
        if count > max_count:
            max_count = count
            most_common_colour = colour
    return [val * 257 for val in most_common_colour]


def pil_to_pixbuf(image):
    """Return a pixbuf created from the PIL <image>."""
    imagestr = image.tostring()
    IS_RGBA = image.mode == 'RGBA'
    return gtk.gdk.pixbuf_new_from_data(imagestr, gtk.gdk.COLORSPACE_RGB,
        IS_RGBA, 8, image.size[0], image.size[1],
        (IS_RGBA and 4 or 3) * image.size[0])


def pixbuf_to_pil(pixbuf):
    """Return a PIL image created from <pixbuf>."""
    dimensions = pixbuf.get_width(), pixbuf.get_height()
    stride = pixbuf.get_rowstride()
    pixels = pixbuf.get_pixels()
    mode = pixbuf.get_has_alpha() and 'RGBA' or 'RGB'
    return Image.frombuffer(mode, dimensions, pixels, 'raw', mode, stride, 1)


def enhance(pixbuf, brightness=1.0, contrast=1.0, saturation=1.0,
  sharpness=1.0, autocontrast=False):
    """Return a modified pixbuf from <pixbuf> where the enhancement operations
    corresponding to each argument has been performed. A value of 1.0 means
    no change. If <autocontrast> is True it overrides the <contrast> value,
    but only if the image mode is supported by ImageOps.autocontrast (i.e.
    it is L or RGB.)
    """
    im = pixbuf_to_pil(pixbuf)
    if brightness != 1.0:
        im = ImageEnhance.Brightness(im).enhance(brightness)
    if autocontrast and im.mode in ('L', 'RGB'):
        im = ImageOps.autocontrast(im, cutoff=0.1)
    elif contrast != 1.0:
        im = ImageEnhance.Contrast(im).enhance(contrast)
    if saturation != 1.0:
        im = ImageEnhance.Color(im).enhance(saturation)
    if sharpness != 1.0:
        im = ImageEnhance.Sharpness(im).enhance(sharpness)
    return pil_to_pixbuf(im)


def get_implied_rotation(pixbuf):
    """Return the implied rotation of the pixbuf, as given by the pixbuf's
    orientation option (the value of which is based on EXIF data etc.).

    The implied rotation is the angle (in degrees) that the raw pixbuf should
    be rotated in order to be displayed "correctly". E.g. a photograph taken
    by a camera that is held sideways might store this fact in its EXIF data,       and the pixbuf loader will set the orientation option correspondingly.
    """
    orientation = pixbuf.get_option('orientation')
    if orientation == '3':
        return 180
    elif orientation == '6':
        return 90
    elif orientation == '8':
        return 270
    return 0
