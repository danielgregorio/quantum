"""
TileFactory - Extrai tiles únicos de uma imagem e cria um tileset otimizado.

Uso:
    python tools/tile_factory.py input.png output_tileset.png --tile-size 16
"""

from PIL import Image
import numpy as np
import hashlib
import json
import os


class TileFactory:
    def __init__(self, tile_width=16, tile_height=16, bg_color=None, tolerance=10):
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.bg_color = bg_color  # RGB tuple or None for auto-detect
        self.tolerance = tolerance

        # Storage
        self.unique_tiles = {}  # hash -> tile_image
        self.tile_map = []      # 2D array of tile hashes
        self.hash_to_id = {}    # hash -> tile_id

    def _detect_bg_color(self, arr):
        """Detecta cor de fundo (pixel do canto superior esquerdo)"""
        return tuple(arr[0, 0, :3])

    def _make_transparent(self, arr, bg_color):
        """Converte cor de fundo para transparente"""
        mask = (
            (np.abs(arr[:,:,0].astype(int) - bg_color[0]) < self.tolerance) &
            (np.abs(arr[:,:,1].astype(int) - bg_color[1]) < self.tolerance) &
            (np.abs(arr[:,:,2].astype(int) - bg_color[2]) < self.tolerance)
        )
        arr[mask, 3] = 0
        return arr

    def _tile_hash(self, tile_arr):
        """Gera hash único para um tile"""
        return hashlib.md5(tile_arr.tobytes()).hexdigest()[:12]

    def _is_empty_tile(self, tile_arr):
        """Verifica se tile é vazio (totalmente transparente)"""
        return np.all(tile_arr[:,:,3] < 10)

    def process(self, image_path):
        """Processa imagem e extrai tiles únicos"""
        # Carregar imagem
        img = Image.open(image_path).convert('RGBA')
        arr = np.array(img)

        print(f"Imagem: {img.size}")

        # Detectar e remover fundo
        bg_color = self.bg_color or self._detect_bg_color(arr)
        print(f"Cor de fundo: RGB{bg_color}")
        arr = self._make_transparent(arr, bg_color)

        # Calcular grid
        cols = img.width // self.tile_width
        rows = img.height // self.tile_height
        print(f"Grid: {cols}x{rows} tiles")

        # Extrair tiles
        self.tile_map = []
        empty_hash = "EMPTY"

        for row in range(rows):
            row_hashes = []
            for col in range(cols):
                x1 = col * self.tile_width
                y1 = row * self.tile_height
                x2 = x1 + self.tile_width
                y2 = y1 + self.tile_height

                tile_arr = arr[y1:y2, x1:x2, :].copy()

                if self._is_empty_tile(tile_arr):
                    row_hashes.append(empty_hash)
                else:
                    tile_hash = self._tile_hash(tile_arr)
                    row_hashes.append(tile_hash)

                    if tile_hash not in self.unique_tiles:
                        self.unique_tiles[tile_hash] = tile_arr

            self.tile_map.append(row_hashes)

        # Criar mapeamento hash -> id
        self.hash_to_id[empty_hash] = 0
        tile_id = 1
        for h in self.unique_tiles.keys():
            self.hash_to_id[h] = tile_id
            tile_id += 1

        print(f"Tiles únicos: {len(self.unique_tiles)}")
        print(f"Tiles vazios ignorados: {sum(1 for row in self.tile_map for h in row if h == empty_hash)}")

        return self

    def create_tileset(self, output_path, max_cols=16):
        """Cria tileset otimizado com tiles únicos"""
        num_tiles = len(self.unique_tiles) + 1  # +1 para tile vazio
        cols = min(max_cols, num_tiles)
        rows = (num_tiles + cols - 1) // cols

        width = cols * self.tile_width
        height = rows * self.tile_height

        # Criar imagem
        tileset = np.zeros((height, width, 4), dtype=np.uint8)

        # Tile 0 = vazio (já é transparente)

        # Adicionar tiles únicos
        for tile_hash, tile_arr in self.unique_tiles.items():
            tile_id = self.hash_to_id[tile_hash]
            col = tile_id % cols
            row = tile_id // cols

            x1 = col * self.tile_width
            y1 = row * self.tile_height

            tileset[y1:y1+self.tile_height, x1:x1+self.tile_width] = tile_arr

        # Salvar
        img = Image.fromarray(tileset)
        img.save(output_path)
        print(f"Tileset salvo: {output_path} ({width}x{height})")

        return output_path

    def get_tile_ids(self):
        """Retorna mapa de IDs dos tiles"""
        return [[self.hash_to_id[h] for h in row] for row in self.tile_map]

    def export_map(self, output_path):
        """Exporta mapa de tiles como JSON"""
        tile_ids = self.get_tile_ids()

        data = {
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "map_width": len(tile_ids[0]) if tile_ids else 0,
            "map_height": len(tile_ids),
            "unique_tiles": len(self.unique_tiles),
            "tiles": tile_ids
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Mapa exportado: {output_path}")
        return data

    def export_quantum_layer(self):
        """Exporta como layer para qg:tilemap"""
        tile_ids = self.get_tile_ids()
        lines = []
        for row in tile_ids:
            lines.append(','.join(str(id) for id in row))
        return '\n'.join(lines)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Uso: python tile_factory.py input.png output_tileset.png")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    factory = TileFactory(tile_width=16, tile_height=16)
    factory.process(input_path)
    factory.create_tileset(output_path)

    # Exportar mapa
    map_path = output_path.replace('.png', '_map.json')
    factory.export_map(map_path)
