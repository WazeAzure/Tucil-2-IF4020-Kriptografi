import struct

class MP3Parser:
    def __init__(self, filename):
        self.filename = filename
        self.frames = []
        self.id3v2 = None
        self.id3v1 = None
        
    def parse(self):
        with open(self.filename, 'rb') as f:
            data = f.read()
        
        offset = 0
        
        if data[:3] == b'ID3':
            self.id3v2 = self._parse_id3v2(data)
            size = struct.unpack('>I', data[6:10])[0]
            size = ((size & 0x7F000000) >> 3) | ((size & 0x7F0000) >> 2) | ((size & 0x7F00) >> 1) | (size & 0x7F)
            offset = 10 + size
        
        while offset < len(data) - 4:
            if data[offset:offset+3] == b'TAG':
                self.id3v1 = self._parse_id3v1(data[offset:])
                break
                
            if data[offset] == 0xFF and (data[offset+1] & 0xE0) == 0xE0:
                frame = self._parse_frame(data[offset:])
                if frame:
                    self.frames.append(frame)
                    offset += frame['frame_size']
                else:
                    offset += 1
            else:
                offset += 1
        
        return {
            'id3v2': self.id3v2,
            'id3v1': self.id3v1,
            'frames': self.frames,
            'duration': sum(f['duration'] for f in self.frames)
        }
    
    def _parse_id3v2(self, data):
        version = data[3]
        flags = data[5]
        return {'version': f'2.{version}', 'flags': flags}
    
    def _parse_id3v1(self, data):
        if len(data) < 128:
            return None
        return {
            'title': data[3:33].decode('latin-1').strip('\x00'),
            'artist': data[33:63].decode('latin-1').strip('\x00'),
            'album': data[63:93].decode('latin-1').strip('\x00'),
            'year': data[93:97].decode('latin-1').strip('\x00'),
            'comment': data[97:127].decode('latin-1').strip('\x00'),
            'genre': data[127]
        }
    
    def _parse_frame(self, data):
        if len(data) < 4:
            return None
            
        header = struct.unpack('>I', data[:4])[0]
        
        version = (header >> 19) & 0x3
        layer = (header >> 17) & 0x3
        bitrate_idx = (header >> 12) & 0xF
        sample_rate_idx = (header >> 10) & 0x3
        padding = (header >> 9) & 0x1
        
        if version == 1 or layer == 0 or bitrate_idx == 0xF or sample_rate_idx == 3:
            return None
        
        versions = {3: 'MPEG 1', 2: 'MPEG 2', 0: 'MPEG 2.5'}
        layers = {3: 1, 2: 2, 1: 3}
        
        bitrates = {
            'MPEG 1': {1: [0,32,64,96,128,160,192,224,256,288,320,352,384,416,448],
                      2: [0,32,48,56,64,80,96,112,128,160,192,224,256,320,384],
                      3: [0,32,40,48,56,64,80,96,112,128,160,192,224,256,320]},
            'MPEG 2': {1: [0,32,48,56,64,80,96,112,128,144,160,176,192,224,256],
                      2: [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160],
                      3: [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160]}
        }
        
        sample_rates = {
            'MPEG 1': [44100, 48000, 32000],
            'MPEG 2': [22050, 24000, 16000],
            'MPEG 2.5': [11025, 12000, 8000]
        }
        
        ver = versions.get(version)
        lay = layers.get(layer)
        
        if not ver or not lay:
            return None
            
        if ver == 'MPEG 2.5':
            bitrate_table = bitrates['MPEG 2']
        else:
            bitrate_table = bitrates.get(ver, {})
        
        bitrate = bitrate_table.get(lay, [])[bitrate_idx] * 1000 if bitrate_idx < len(bitrate_table.get(lay, [])) else 0
        sample_rate = sample_rates.get(ver, [])[sample_rate_idx] if sample_rate_idx < len(sample_rates.get(ver, [])) else 0
        
        if bitrate == 0 or sample_rate == 0:
            return None
        
        if lay == 1:
            frame_size = int((12 * bitrate / sample_rate + padding) * 4)
            samples = 384
        else:
            frame_size = int(144 * bitrate / sample_rate + padding)
            samples = 1152
        
        return {
            'version': ver,
            'layer': lay,
            'bitrate': bitrate,
            'sample_rate': sample_rate,
            'frame_size': frame_size,
            'duration': samples / sample_rate
        }


if __name__ == '__main__':
    parser = MP3Parser('stego.mp3')
    info = parser.parse()
    print(f"Duration: {info['duration']:.2f}s")
    print(f"Total frames: {len(info['frames'])}")
    if info['id3v1']:
        print(f"Title: {info['id3v1']['title']}")
        print(f"Artist: {info['id3v1']['artist']}")