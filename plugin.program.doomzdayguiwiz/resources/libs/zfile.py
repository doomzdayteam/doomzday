#Modded just for Kodi
############################################################################
#                             /T /I                                        #
#                              / |/ | .-~/                                 #
#                          T\ Y  I  |/  /  _                               #
#         /T               | \I  |  I  Y.-~/                               #
#        I l   /I       T\ |  |  l  |  T  /                                #
#     T\ |  \ Y l  /T   | \I  l   \ `  l Y                                 #
# __  | \l   \l  \I l __l  l   \   `  _. |                                 #
# \ ~-l  `\   `\  \  \ ~\  \   `. .-~   |                                  #
#  \   ~-. "-.  `  \  ^._ ^. "-.  /  \   |                                 #
#.--~-._  ~-  `  _  ~-_.-"-." ._ /._ ." ./                                 #
# >--.  ~-.   ._  ~>-"    "\   7   7   ]                                   #
#^.___~"--._    ~-{  .-~ .  `\ Y . /    |                                  #
# <__ ~"-.  ~       /_/   \   \I  Y   : |                                  #
#   ^-.__           ~(_/   \   >._:   | l______                            #
#       ^--.,___.-~"  /_/   !  `-.~"--l_ /     ~"-.                        #
#              (_/ .  ~(   /'     "~"--,Y   -=b-. _)                       #
#               (_/ .  \  :           / l      c"~o \                      #
#                \ /    `.    .     .^   \_.-~"~--.  )                     #
#                 (_/ .   `  /     /       !       )/                      #
#                  / / _.   '.   .':      /        '                       #
#                  ~(_/ .   /    _  `  .-<_                                #
#                    /_/ . ' .-~" `.  / \  \          ,z=.  Python Team    #
#                    ~( /   '  :   | K   "-.~-.______//   Original Author  #
#                      "-,.    l   I/ \_    __{--->._(==.                  #
#                       //(     \  <    ~"~"     //                        #
#                      /' /\     \  \     ,v=.  ((     Fire TV Guru        #
#                    .^. / /\     "  }__ //===-  `    Modded for Kodi 18   #
#                   / / ' '  "-.,__ {---(==-                               #
#                 .^ '       :  T  ~"   ll                                 #
#                / .  .  . : | :!        \                                 #
#               (_/  /   | | j-"          ~^                               #
#                 ~-<_(_.^-~"                                              #
#                                                                          #
############################################################################
# Cleaned for Kodi 20+ (Python 3 only). Legacy FTG/Kodi 18 code removed for clarity.

import io
import struct
import os
import sys
import time
import stat
import shutil
import re
import zlib
import binascii
import string
try:
    import xbmc
except ImportError:
    xbmc = None

class BadZipfile(Exception):
    pass

class LargeZipFile(Exception):
    pass

# Constants for ZIP file structures
_ECD_SIGNATURE = 0
_ECD_DISK_NUMBER = 1
_ECD_DISK_START = 2
_ECD_ENTRIES_THIS_DISK = 3
_ECD_ENTRIES_TOTAL = 4
_ECD_SIZE = 5
_ECD_OFFSET = 6
_ECD_COMMENT_SIZE = 7
_ECD_COMMENT = 8
_ECD_LOCATION = 9

_CD_SIGNATURE = 0
_CD_CREATE_VERSION = 1
_CD_CREATE_SYSTEM = 2
_CD_EXTRACT_VERSION = 3
_CD_RESERVED = 4
_CD_FLAG_BITS = 5
_CD_COMPRESS_TYPE = 6
_CD_TIME = 7
_CD_DATE = 8
_CD_CRC = 9
_CD_COMPRESSED_SIZE = 10
_CD_UNCOMPRESSED_SIZE = 11
_CD_FILENAME_LENGTH = 12
_CD_EXTRA_FIELD_LENGTH = 13
_CD_COMMENT_LENGTH = 14
_CD_DISK_NUMBER_START = 15
_CD_INTERNAL_ATTR = 16
_CD_EXTERNAL_ATTR = 17
_CD_LOCAL_HEADER_OFFSET = 18

_FH_SIGNATURE = 0
_FH_EXTRACT_VERSION = 1
_FH_RESERVED = 2
_FH_FLAG_BITS = 3
_FH_COMPRESS_TYPE = 4
_FH_TIME = 5
_FH_DATE = 6
_FH_CRC = 7
_FH_COMPRESSED_SIZE = 8
_FH_UNCOMPRESSED_SIZE = 9
_FH_FILENAME_LENGTH = 10
_FH_EXTRA_FIELD_LENGTH = 11

ZIP_STORED = 0
ZIP_DEFLATED = 8
ZIP_MAX_COMMENT = (1 << 16) - 1
ZIP64_LIMIT = (1 << 31) - 1
ZIP_FILECOUNT_LIMIT = (1 << 16) - 1

structCentralDir = '<4s2B4H3L5H2L'
sizeCentralDir = struct.calcsize(structCentralDir)
structFileHeader = '<4s2B4H3L2H'
sizeFileHeader = struct.calcsize(structFileHeader)
structEndArchive = '<4s4H2LH'
sizeEndCentDir = struct.calcsize(structEndArchive)
structEndArchive64 = '<4sQ2H2L4Q'
sizeEndCentDir64 = struct.calcsize(structEndArchive64)
structEndArchive64Locator = '<4sLQL'
sizeEndCentDir64Locator = struct.calcsize(structEndArchive64Locator)

stringCentralDir = b'PK\x01\x02'
stringFileHeader = b'PK\x03\x04'
stringEndArchive = b'PK\x05\x06'
stringEndArchive64 = b'PK\x06\x06'
stringEndArchive64Locator = b'PK\x06\x07'

def _check_zipfile(fp):
    try:
        if _EndRecData(fp):
            return True
    except IOError:
        pass
    return False

def is_zipfile(filename):
    try:
        if hasattr(filename, "read"):
            return _check_zipfile(fp=filename)
        else:
            with open(filename, "rb") as fp:
                return _check_zipfile(fp)
    except IOError:
        return False

def _EndRecData64(fpin, offset, endrec):
    try:
        fpin.seek(offset - sizeEndCentDir64Locator, 2)
    except IOError:
        return endrec
    data = fpin.read(sizeEndCentDir64Locator)
    if len(data) != sizeEndCentDir64Locator:
        return endrec
    sig, diskno, reloff, disks = struct.unpack(structEndArchive64Locator, data)
    if sig != stringEndArchive64Locator:
        return endrec
    if diskno != 0 or disks != 1:
        raise BadZipfile("zipfiles that span multiple disks are not supported")
    fpin.seek(offset - sizeEndCentDir64Locator - sizeEndCentDir64, 2)
    data = fpin.read(sizeEndCentDir64)
    if len(data) != sizeEndCentDir64:
        return endrec
    sig, sz, create_version, read_version, disk_num, disk_dir, \
        dircount, dircount2, dirsize, diroffset = struct.unpack(structEndArchive64, data)
    if sig != stringEndArchive64:
        return endrec
    endrec[_ECD_SIGNATURE] = sig
    endrec[_ECD_DISK_NUMBER] = disk_num
    endrec[_ECD_DISK_START] = disk_dir
    endrec[_ECD_ENTRIES_THIS_DISK] = dircount
    endrec[_ECD_ENTRIES_TOTAL] = dircount2
    endrec[_ECD_SIZE] = dirsize
    endrec[_ECD_OFFSET] = diroffset
    return endrec

def _EndRecData(fpin):
    fpin.seek(0, 2)
    filesize = fpin.tell()
    try:
        fpin.seek(-sizeEndCentDir, 2)
    except IOError:
        return None
    data = fpin.read()
    if (len(data) == sizeEndCentDir and
        data[0:4] == stringEndArchive and
        data[-2:] == b"\000\000"):
        endrec = struct.unpack(structEndArchive, data)
        endrec = list(endrec)
        endrec.append(b"")
        endrec.append(filesize - sizeEndCentDir)
        return _EndRecData64(fpin, -sizeEndCentDir, endrec)
    maxCommentStart = max(filesize - (1 << 16) - sizeEndCentDir, 0)
    fpin.seek(maxCommentStart, 0)
    data = fpin.read()
    start = data.rfind(stringEndArchive)
    if start >= 0:
        recData = data[start:start+sizeEndCentDir]
        if len(recData) != sizeEndCentDir:
            return None
        endrec = list(struct.unpack(structEndArchive, recData))
        commentSize = endrec[_ECD_COMMENT_SIZE]
        comment = data[start+sizeEndCentDir:start+sizeEndCentDir+commentSize]
        endrec.append(comment)
        endrec.append(maxCommentStart + start)
        return _EndRecData64(fpin, maxCommentStart + start - filesize, endrec)
    return None

class ZipInfo(object):
    __slots__ = (
        'orig_filename', 'filename', 'date_time', 'compress_type', 'comment', 'extra',
        'create_system', 'create_version', 'extract_version', 'reserved', 'flag_bits',
        'volume', 'internal_attr', 'external_attr', 'header_offset', 'CRC',
        'compress_size', 'file_size', '_raw_time',
    )

    def __init__(self, filename="NoName", date_time=(1980,1,1,0,0,0)):
        self.orig_filename = filename
        null_byte = filename.find(chr(0))
        if null_byte >= 0:
            filename = filename[0:null_byte]
        if os.sep != "/" and os.sep in filename:
            filename = filename.replace(os.sep, "/")
        self.filename = filename
        self.date_time = date_time
        if date_time[0] < 1980:
            raise ValueError('ZIP does not support timestamps before 1980')
        self.compress_type = ZIP_STORED
        self.comment = ""
        self.extra = ""
        self.create_system = 0 if sys.platform == 'win32' else 3
        self.create_version = 20
        self.extract_version = 20
        self.reserved = 0
        self.flag_bits = 0
        self.volume = 0
        self.internal_attr = 0
        self.external_attr = 0

    def FileHeader(self, zip64=None):
        dt = self.date_time
        dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
        dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
        if self.flag_bits & 0x08:
            CRC = compress_size = file_size = 0
        else:
            CRC = self.CRC
            compress_size = self.compress_size
            file_size = self.file_size
        extra = self.extra
        if zip64 is None:
            zip64 = file_size > ZIP64_LIMIT or compress_size > ZIP64_LIMIT
        if zip64:
            fmt = '<HHQQ'
            extra = extra + struct.pack(fmt, 1, struct.calcsize(fmt)-4, file_size, compress_size)
        if file_size > ZIP64_LIMIT or compress_size > ZIP64_LIMIT:
            if not zip64:
                raise LargeZipFile("Filesize would require ZIP64 extensions")
            file_size = 0xffffffff
            compress_size = 0xffffffff
            self.extract_version = max(45, self.extract_version)
            self.create_version = max(45, self.extract_version)
        filename, flag_bits = self._encodeFilenameFlags()
        header = struct.pack(structFileHeader, stringFileHeader,
                 self.extract_version, self.reserved, flag_bits,
                 self.compress_type, dostime, dosdate, CRC,
                 compress_size, file_size,
                 len(filename), len(extra))
        return header + filename + extra

    def _encodeFilenameFlags(self):
        if isinstance(self.filename, str):
            try:
                return self.filename.encode('ascii'), self.flag_bits
            except UnicodeEncodeError:
                return self.filename.encode('utf-8'), self.flag_bits | 0x800
        else:
            return self.filename, self.flag_bits

    def _decodeFilename(self):
        if self.flag_bits & 0x800:
            return self.filename.decode('utf-8')
        else:
            return self.filename

    def _decodeExtra(self):
        extra = self.extra
        unpack = struct.unpack
        while len(extra) >= 4:
            tp, ln = unpack('<HH', extra[:4])
            if tp == 1:
                if ln >= 24:
                    counts = unpack('<QQQ', extra[4:28])
                elif ln == 16:
                    counts = unpack('<QQ', extra[4:20])
                elif ln == 8:
                    counts = unpack('<Q', extra[4:12])
                elif ln == 0:
                    counts = ()
                else:
                    raise RuntimeError("Corrupt extra field %s"%(ln,))
                idx = 0
                if self.file_size in (0xffffffffffffffff, 0xffffffff):
                    self.file_size = counts[idx]
                    idx += 1
                if self.compress_size == 0xFFFFFFFF:
                    self.compress_size = counts[idx]
                    idx += 1
                if self.header_offset == 0xffffffff:
                    self.header_offset = counts[idx]
                    idx += 1
            extra = extra[ln+4:]

class _ZipDecrypter:
    def _GenerateCRCTable():
        poly = 0xedb88320
        table = [0] * 256
        for i in range(256):
            crc = i
            for j in range(8):
                if crc & 1:
                    crc = ((crc >> 1) & 0x7FFFFFFF) ^ poly
                else:
                    crc = ((crc >> 1) & 0x7FFFFFFF)
            table[i] = crc
        return table
    crctable = _GenerateCRCTable()

    def _crc32(self, ch, crc):
        return ((crc >> 8) & 0xffffff) ^ self.crctable[(crc ^ ord(ch)) & 0xff]

    def __init__(self, pwd):
        self.key0 = 305419896
        self.key1 = 591751049
        self.key2 = 878082192
        for p in pwd:
            self._UpdateKeys(p)

    def _UpdateKeys(self, c):
        self.key0 = self._crc32(c, self.key0)
        self.key1 = (self.key1 + (self.key0 & 255)) & 4294967295
        self.key1 = (self.key1 * 134775813 + 1) & 4294967295
        self.key2 = self._crc32(chr((self.key1 >> 24) & 255), self.key2)

    def __call__(self, c):
        c = ord(c)
        k = self.key2 | 2
        c = c ^ (((k * (k^1)) >> 8) & 255)
        c = chr(c)
        self._UpdateKeys(c)
        return c

compressor_names = {
    0: 'store', 1: 'shrink', 2: 'reduce', 3: 'reduce', 4: 'reduce', 5: 'reduce',
    6: 'implode', 7: 'tokenize', 8: 'deflate', 9: 'deflate64', 10: 'implode',
    12: 'bzip2', 14: 'lzma', 18: 'terse', 19: 'lz77', 97: 'wavpack', 98: 'ppmd',
}

class ZipExtFile(io.BufferedIOBase):
    MAX_N = 1 << 31 - 1
    MIN_READ_SIZE = 4096
    PATTERN = re.compile(r'^(?P<chunk>[^\r\n]+)|(?P<newline>\n|\r\n?)')

    def __init__(self, fileobj, mode, zipinfo, decrypter=None, close_fileobj=False):
        self._fileobj = fileobj
        self._decrypter = decrypter
        self._close_fileobj = close_fileobj
        self._compress_type = zipinfo.compress_type
        self._compress_size = zipinfo.compress_size
        self._compress_left = zipinfo.compress_size
        if self._compress_type == ZIP_DEFLATED:
            self._decompressor = zlib.decompressobj(-15)
        elif self._compress_type != ZIP_STORED:
            descr = compressor_names.get(self._compress_type)
            if descr:
                raise NotImplementedError("compression type %d (%s)" % (self._compress_type, descr))
            else:
                raise NotImplementedError("compression type %d" % (self._compress_type,))
        self._unconsumed = ''
        self._readbuffer = ''
        self._running_crc = binascii.crc32(b'') & 0xffffffff
        self._universal = 'U' in mode
        self.newlines = None
        if self._decrypter is not None:
            self._compress_left -= 12
        self.mode = mode
        self.name = zipinfo.filename
        if hasattr(zipinfo, 'CRC'):
            self._expected_crc = zipinfo.CRC
            self._running_crc = binascii.crc32(b'') & 0xffffffff
        else:
            self._expected_crc = None

    def readline(self, limit=-1):
        if not self._universal and limit < 0:
            i = self._readbuffer.find('\n', self._offset) + 1
            if i > 0:
                line = self._readbuffer[self._offset: i]
                self._offset = i
                return line
        if not self._universal:
            return io.BufferedIOBase.readline(self, limit)
        line = ''
        while limit < 0 or len(line) < limit:
            readahead = self.peek(2)
            if readahead == '':
                return line
            match = self.PATTERN.search(readahead)
            newline = match.group('newline')
            if newline is not None:
                if self.newlines is None:
                    self.newlines = []
                if newline not in self.newlines:
                    self.newlines.append(newline)
                self._offset += len(newline)
                return line + '\n'
            chunk = match.group('chunk')
            if limit >= 0:
                chunk = chunk[: limit - len(line)]
            self._offset += len(chunk)
            line += chunk
        return line

    def peek(self, n=1):
        if n > len(self._readbuffer) - self._offset:
            chunk = self.read(n)
            if len(chunk) > self._offset:
                self._readbuffer = chunk + self._readbuffer[self._offset:]
                self._offset = 0
            else:
                self._offset -= len(chunk)
        return self._readbuffer[self._offset: self._offset + 512]

    def readable(self):
        return True

    def read(self, n=-1):
        buf = ''
        if n is None:
            n = -1
        while True:
            if n < 0:
                data = self.read1(n)
            elif n > len(buf):
                data = self.read1(n - len(buf))
            else:
                return buf
            if len(data) == 0:
                return buf
            buf += data

    def _update_crc(self, newdata, eof):
        if self._expected_crc is None:
            return
        self._running_crc = binascii.crc32(newdata, self._running_crc) & 0xffffffff
        if eof and self._running_crc != self._expected_crc:
            raise BadZipfile("Bad CRC-32 for file %r" % self.name)

    def read1(self, n):
        if n < 0 or n is None:
            n = self.MAX_N
        len_readbuffer = len(self._readbuffer) - self._offset
        if self._compress_left > 0 and n > len_readbuffer + len(self._unconsumed):
            nbytes = n - len_readbuffer - len(self._unconsumed)
            nbytes = max(nbytes, self.MIN_READ_SIZE)
            nbytes = min(nbytes, self._compress_left)
            data = self._fileobj.read(nbytes)
            self._compress_left -= len(data)
            if data and self._decrypter is not None:
                data = ''.join(map(self._decrypter, data))
            if self._compress_type == ZIP_STORED:
                self._update_crc(data, eof=(self._compress_left==0))
                self._readbuffer = self._readbuffer[self._offset:] + data
                self._offset = 0
            else:
                self._unconsumed += data
        if (len(self._unconsumed) > 0 and n > len_readbuffer and
            self._compress_type == ZIP_DEFLATED):
            data = self._decompressor.decompress(
                self._unconsumed,
                max(n - len_readbuffer, self.MIN_READ_SIZE)
            )
            self._unconsumed = self._decompressor.unconsumed_tail
            eof = len(self._unconsumed) == 0 and self._compress_left == 0
            if eof:
                data += self._decompressor.flush()
            self._update_crc(data, eof=eof)
            self._readbuffer = self._readbuffer[self._offset:] + data
            self._offset = 0
        data = self._readbuffer[self._offset: self._offset + n]
        self._offset += len(data)
        return data

def platform():
    if xbmc is not None:
        if xbmc.getCondVisibility('system.platform.android'): return 'android'
        elif xbmc.getCondVisibility('system.platform.linux'): return 'linux'
        elif xbmc.getCondVisibility('system.platform.linux.Raspberrypi'): return 'linux'
        elif xbmc.getCondVisibility('system.platform.windows'): return 'windows'
        elif xbmc.getCondVisibility('system.platform.osx'): return 'osx'
        elif xbmc.getCondVisibility('system.platform.atv2'): return 'atv2'
        elif xbmc.getCondVisibility('system.platform.ios'): return 'ios'
        elif xbmc.getCondVisibility('system.platform.darwin'): return 'ios'
    return 'unknown'

class ZipFile(object):
    fp = None

    def __init__(self, file, mode="r", compression=ZIP_STORED, allowZip64=False):
        if mode not in ("r", "w", "a"):
            raise RuntimeError('ZipFile() requires mode "r", "w", or "a"')
        if compression == ZIP_STORED:
            pass
        elif compression == ZIP_DEFLATED:
            if not zlib:
                raise RuntimeError("Compression requires the (missing) zlib module")
        else:
            raise RuntimeError("That compression method is not supported")
        self._allowZip64 = allowZip64
        self._didModify = False
        self.debug = 0
        self.NameToInfo = {}
        self.filelist = []
        self.compression = compression
        self.mode = key = mode.replace('b', '')[0]
        self.pwd = None
        self._comment = ''
        if isinstance(file, str):
            self._filePassed = 0
            self.filename = file
            modeDict = {'r': 'rb', 'w': 'wb', 'a': 'r+b'}
            try:
                self.fp = open(file, modeDict[mode])
            except IOError:
                if mode == 'a':
                    mode = key = 'w'
                    self.fp = open(file, modeDict[mode])
                else:
                    raise
        else:
            self._filePassed = 1
            self.fp = file
            self.filename = getattr(file, 'name', None)
        try:
            if key == 'r':
                self._RealGetContents()
            elif key == 'w':
                self._didModify = True
            elif key == 'a':
                try:
                    self._RealGetContents()
                    self.fp.seek(self.start_dir, 0)
                except BadZipfile:
                    self.fp.seek(0, 2)
                    self._didModify = True
            else:
                raise RuntimeError('Mode must be "r", "w" or "a"')
        except:
            fp = self.fp
            self.fp = None
            if not self._filePassed:
                fp.close()
            raise

    # ...rest of the ZipFile methods as in your previous code, with proper indentation and no legacy code...