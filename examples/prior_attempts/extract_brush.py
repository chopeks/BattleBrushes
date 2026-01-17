import struct
import xml.etree.ElementTree as ET
from PIL import Image
import argparse

class SpritesheetParser:
    def __init__(self, spritesheet_path):
        with Image.open(spritesheet_path) as img:
            self.width, self.height = img.size

    def parse_sprite_data(self, data, sprite_id):
        width, height, offsetX, offsetY = struct.unpack('<hhhh', data[:8])
        f = struct.unpack('<H', data[8:10])[0]
        ic = struct.unpack('<I', data[10:14])[0]
        left, right, top, bottom = struct.unpack('<hhhh', data[14:22])

        f_hex = f"{f:04X}"
        f_hex = f_hex[2:] + f_hex[:2]
        ic_hex = f"FF{ic:06X}"

        return {
            'width': width if width != 0 else None,
            'height': height if height != 0 else None,
            'offsetX': offsetX if offsetX != 0 else None,
            'offsetY': offsetY if offsetY != 0 else None,
            'f': f_hex,
            'ic': ic_hex,
            'left': left if left != 0 else None,
            'right': right if right != 0 else None,
            'top': top if top != 0 else None,
            'bottom': bottom if bottom != 0 else None
        }

    def read_null_terminated_string(self, data, offset):
        end = data.index(b'\x00', offset)
        return data[offset:end].decode('ascii')

    def parse_input_file(self, file_path):
        with open(file_path, 'rb') as f:
            data = f.read()

        offset = 0
        sprites = []
        while offset < len(data):
            if data[offset:offset+6] == b'detail':
                img_path = self.read_null_terminated_string(data, offset)
                sprite_id = img_path.split('\\')[-1].split('.')[0]
                
                offset += len(img_path) + 1
                binary_data = data[offset:offset+22]
                
                parsed_data = self.parse_sprite_data(binary_data, sprite_id)
                sprite_element = self.create_sprite_xml(sprite_id, img_path, parsed_data)
                sprites.append(sprite_element)
                
                offset += 22
            else:
                offset += 1

        return sprites

    def create_sprite_xml(self, sprite_id, img_path, data):
        sprite = ET.Element('sprite')
        sprite.set('id', sprite_id)
        sprite.set('img', img_path)
        for key, value in data.items():
            if value is not None:
                sprite.set(key, str(value))
        return sprite

    def create_brush_xml(self, sprites, brush_name, version):
        brush = ET.Element('brush')
        brush.set('name', brush_name)
        brush.set('version', version)
        for sprite in sprites:
            brush.append(sprite)
        return brush

def main():
    parser = argparse.ArgumentParser(description='Parse spritesheet data and generate XML')
    parser.add_argument('spritesheet', help='Path to the spritesheet image')
    parser.add_argument('input_file', help='Path to the input binary file')
    parser.add_argument('output_file', help='Path for the output XML file')
    parser.add_argument('--brush_name', default='gfx/legend_detail.png', help='Name for the brush element')
    parser.add_argument('--version', default='17', help='Version for the brush element')
    
    args = parser.parse_args()

    spritesheet_parser = SpritesheetParser(args.spritesheet)
    sprites = spritesheet_parser.parse_input_file(args.input_file)
    brush = spritesheet_parser.create_brush_xml(sprites, args.brush_name, args.version)

    # Convert to string and remove XML declaration
    xml_string = ET.tostring(brush, encoding='unicode')
    xml_string = xml_string.split('?>\n', 1)[-1]  # Remove XML declaration if present
    
    with open(args.output_file, 'w', encoding='utf-8') as f:
        f.write(xml_string)

    print(f"XML output written to {args.output_file}")

if __name__ == "__main__":
    main()
