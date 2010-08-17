"""thumbnail.py - Thumbnail module for Comix implementing (most of) the
freedesktop.org "standard" at http://jens.triq.net/thumbnail-spec/

Only normal size (i.e. 128x128 px) thumbnails are supported.
"""

import os
from urllib import pathname2url, url2pathname
try: # The md5 module is deprecated as of Python 2.5, replaced by hashlib.
    from hashlib import md5
except ImportError:
    from md5 import new as md5
import re
import shutil
import tempfile

import gtk
import Image

import archive
import constants
import filehandler

_thumbdir = os.path.join(constants.HOME_DIR, '.thumbnails/normal')


def get_thumbnail(path, create=True, dst_dir=_thumbdir):
    """Return a thumbnail pixbuf for the file at <path> by looking in the
    directory of stored thumbnails. If a thumbnail for the file doesn't
    exist we create a thumbnail pixbuf from the original. If <create>
    is True we also save this new thumbnail in the thumbnail directory.
    If no thumbnail for <path> can be produced (for whatever reason),
    return None.

    Images and archives are handled transparently. Note though that
    None is always returned for archives where no thumbnail already exist
    if <create> is False, since re-creating the thumbnail on the fly each
    time would be too costly.

    If <dst_dir> is set it is the base thumbnail directory, if not we use
    the default .thumbnails/normal/.
    """
    thumbpath = _path_to_thumbpath(path, dst_dir)
    if not os.path.exists(thumbpath):
        return _get_new_thumbnail(path, create, dst_dir)
    try:
        info = Image.open(thumbpath).info
        try:
            mtime = int(info['Thumb::MTime'])
        except Exception:
            mtime = -1
        if os.stat(path).st_mtime != mtime:
            return _get_new_thumbnail(path, create, dst_dir)
        return gtk.gdk.pixbuf_new_from_file(thumbpath)
    except Exception:
        return None


def delete_thumbnail(path, dst_dir=_thumbdir):
    """Delete the thumbnail (if it exists) for the file at <path>.
    
    If <dst_dir> is set it is the base thumbnail directory, if not we use
    the default .thumbnails/normal/.
    """
    thumbpath = _path_to_thumbpath(path, dst_dir)
    if os.path.isfile(thumbpath):
        try:
            os.remove(thumbpath)
        except Exception:
            pass


def _get_new_thumbnail(path, create, dst_dir):
    """Return a new thumbnail pixbuf for the file at <path>. If <create> is
    True we also save it to disk with <dst_dir> as the base thumbnail
    directory.
    """
    if archive.archive_mime_type(path) is not None:
        if create:
            return _get_new_archive_thumbnail(path, dst_dir)
        return None
    if create:
        return _create_thumbnail(path, dst_dir)
    return _get_pixbuf128(path)


def _get_new_archive_thumbnail(path, dst_dir):
    """Return a new thumbnail pixbuf for the archive at <path>, and save it
    to disk; <dst_dir> is the base thumbnail directory.
    """
    extractor = archive.Extractor()
    tmpdir = tempfile.mkdtemp(prefix='comix_archive_thumb.')
    condition = extractor.setup(path, tmpdir)
    files = extractor.get_files()
    wanted = _guess_cover(files)
    if wanted is None:
        return None
    extractor.set_files([wanted])
    extractor.extract()
    image_path = os.path.join(tmpdir, wanted)
    condition.acquire()
    while not extractor.is_ready(wanted):
        condition.wait()
    condition.release()
    pixbuf = _create_thumbnail(path, dst_dir, image_path=image_path)
    shutil.rmtree(tmpdir)
    return pixbuf


def _create_thumbnail(path, dst_dir, image_path=None):
    """Create a thumbnail from the file at <path> and store it if it is
    larger than 128x128 px. A pixbuf for the thumbnail is returned.

    <dst_dir> is the base thumbnail directory (usually ~/.thumbnails/normal).

    If <image_path> is not None it is used as the path to the image file
    actually used to create the thumbnail image, although the created
    thumbnail will still be saved as if for <path>.
    """
    if image_path is None:
        image_path = path
    pixbuf = _get_pixbuf128(image_path)
    if pixbuf is None:
        return None
    mime, width, height = gtk.gdk.pixbuf_get_file_info(image_path)
    if width <= 128 and height <= 128:
        return pixbuf
    mime = mime['mime_types'][0]
    uri = 'file://' + pathname2url(os.path.normpath(path))
    thumbpath = _uri_to_thumbpath(uri, dst_dir)
    stat = os.stat(path)
    mtime = str(int(stat.st_mtime))
    size = str(stat.st_size)
    width = str(width)
    height = str(height)
    tEXt_data = {
        'tEXt::Thumb::URI':           uri,
        'tEXt::Thumb::MTime':         mtime,
        'tEXt::Thumb::Size':          size,
        'tEXt::Thumb::Mimetype':      mime,
        'tEXt::Thumb::Image::Width':  width,
        'tEXt::Thumb::Image::Height': height,
        'tEXt::Software':             'Comix %s' % constants.VERSION
    }
    try:
        if not os.path.isdir(dst_dir):
            os.makedirs(dst_dir, 0700)
        pixbuf.save(thumbpath + '-comixtemp', 'png', tEXt_data)
        os.rename(thumbpath + '-comixtemp', thumbpath)
        os.chmod(thumbpath, 0600)
    except Exception:
        print '! thumbnail.py: Could not write', thumbpath, '\n'
    return pixbuf


def _path_to_thumbpath(path, dst_dir):
    uri = 'file://' + pathname2url(os.path.normpath(path))
    return _uri_to_thumbpath(uri, dst_dir)


def _uri_to_thumbpath(uri, dst_dir):
    """Return the full path to the thumbnail for <uri> when <dst_dir> the base
    thumbnail directory.
    """
    md5hash = md5(uri).hexdigest()
    thumbpath = os.path.join(dst_dir, md5hash + '.png')
    return thumbpath


def _get_pixbuf128(path):
    try:
        return gtk.gdk.pixbuf_new_from_file_at_size(path, 128, 128)
    except Exception:
        return None


def _guess_cover(files):
    """Return the filename within <files> that is the most likely to be the
    cover of an archive using some simple heuristics.
    """
    filehandler.alphanumeric_sort(files)
    ext_re = re.compile(r'\.(jpg|jpeg|png|gif|tif|tiff|bmp)\s*$', re.I)
    front_re = re.compile('(cover|front)', re.I)
    images = filter(ext_re.search, files)
    candidates = filter(front_re.search, images)
    candidates = [c for c in candidates if 'back' not in c.lower()]
    if candidates:
        return candidates[0]
    if images:
        return images[0]
    return None
