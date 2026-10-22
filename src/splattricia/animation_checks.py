"""Explicit development checks; never run during ordinary conversion."""
from pathlib import Path
import struct

from PIL import Image


def _boxes(data, start=0, end=None):
    end = len(data) if end is None else end
    while start + 8 <= end:
        size, kind = struct.unpack_from('>I4s', data, start)
        header = 8
        if size == 1:
            size = struct.unpack_from('>Q', data, start + 8)[0]
            header = 16
        elif size == 0:
            size = end - start
        if size < header or start + size > end:
            raise AssertionError('Invalid AVIF container box')
        yield kind, start + header, start + size
        start += size
    assert start == end


def check_avif_loop(path):
    """ISO BMFF loop flag and indefinite track duration must both be present."""
    data = Path(path).read_bytes()
    loops, infinite_tracks = [], []
    def walk(start, end):
        for kind, body, stop in _boxes(data, start, end):
            if kind in (b'moov', b'trak', b'edts'):
                walk(body, stop)
            elif kind == b'elst':
                loops.append(bool(int.from_bytes(data[body + 1:body + 4], 'big') & 1))
            elif kind == b'tkhd':
                version = data[body]
                offset, length = (28, 8) if version == 1 else (20, 4)
                duration = int.from_bytes(data[body + offset:body + offset + length], 'big')
                infinite_tracks.append(duration == (1 << (length * 8)) - 1)
    walk(0, len(data))
    assert loops and all(loops) and infinite_tracks and all(infinite_tracks)


def check_animation(path, size, duration_ms, expected_frames=None):
    path = Path(path)
    duration = 0
    with Image.open(path) as image:
        assert image.size == tuple(size)
        frames = image.n_frames
        if expected_frames is not None:
            assert frames == expected_frames, (frames, expected_frames)
        for index in range(frames):
            image.seek(index)
            image.load()
            duration += image.info['duration']
    assert abs(duration - duration_ms) <= 1, (duration, duration_ms)
    if path.suffix == '.avif':
        check_avif_loop(path)
    return dict(format=path.suffix[1:], frames=frames, duration_ms=duration,
                width=size[0], height=size[1], infinite_loop=True)
