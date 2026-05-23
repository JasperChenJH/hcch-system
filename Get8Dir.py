import math
import numpy as np

class Stroke8DirVectorAdjust:
    def __init__(self):
        # ===================== 【已修复】标准8方向 (dx, dy)，(0,1)=向上 =====================
        self.dirs = [
            (0, 1),    # D0: 上    ✅ 正确
            (1, 1),    # D1: 右上  ✅
            (1, 0),    # D2: 右    ✅
            (1, -1),   # D3: 右下  ✅
            (0, -1),   # D4: 下    ✅
            (-1, -1),  # D5: 左下  ✅
            (-1, 0),   # D6: 左    ✅
            (-1, 1)    # D7: 左上  ✅
        ]

    def __get_initial_vector(self, x: int, y: int, binary_img: np.ndarray, dx: int, dy: int):
        cy, cx = y, x
        total_dy, total_dx = 0, 0
        steps = 0
        h, w = binary_img.shape

        while True:
            nx = cx + dx
            ny = cy + dy
            if not (0 <= ny < h and 0 <= nx < w) or binary_img[ny, nx] == 255:
                break
            cy, cx = ny, nx
            total_dy += dy
            total_dx += dx
            steps += 1

        return (total_dx, total_dy, steps)

    def __get_initial_8vectors(self, x: int, y, binary_img: np.ndarray):
        vectors = []
        for dx, dy in self.dirs:
            vec = self.__get_initial_vector(x, y, binary_img, dx, dy)
            vectors.append(vec)
        return vectors

    def __vector_add(self, v1, v2):
        x1, y1, _ = v1
        x2, y2, _ = v2
        return (x1 + x2, y1 + y2)

    def __normalize_direction(self, vec):
        x, y = vec
        if x == 0 and y == 0:
            return None
        length = math.hypot(x, y)
        nx = round(x / length)
        ny = round(y / length)
        return (nx, ny)

    def __probe_along_direction(self, x: int, y: int, binary_img: np.ndarray, dx: int, dy: int):
        cy, cx = y, x
        total_dy, total_dx = 0, 0
        steps = 0
        h, w = binary_img.shape

        while True:
            nx = cx + dx
            ny = cy + dy
            if not (0 <= ny < h and 0 <= nx < w) or binary_img[ny, nx] == 255:
                break
            cy, cx = ny, nx
            total_dy += dy
            total_dx += dx
            steps += 1

        return (total_dx, total_dy, steps)

    def adjust_8vectors(self, x: int, y: int, binary_img: np.ndarray, sync_update: bool = False):
        vectors = self.__get_initial_8vectors(x, y, binary_img)
        if sync_update:
            vectors_old = vectors.copy()

        for i in range(8):
            if sync_update:
                v_prev = vectors_old[(i - 1) % 8]
                v_next = vectors_old[(i + 1) % 8]
            else:
                v_prev = vectors[(i - 1) % 8]
                v_next = vectors[(i + 1) % 8]

            v_current = vectors[i]
            u1 = self.__vector_add(v_current, v_prev)
            u2 = self.__vector_add(v_current, v_next)

            candidates = []
            dx_a, dy_a = self.dirs[i]
            candidates.append((dx_a, dy_a))

            dir_b = self.__normalize_direction(u1)
            if dir_b is not None:
                candidates.append(dir_b)

            dir_c = self.__normalize_direction(u2)
            if dir_c is not None:
                candidates.append(dir_c)

            probe_results = []
            for dx, dy in candidates:
                vec = self.__probe_along_direction(x, y, binary_img, dx, dy)
                probe_results.append(vec)

            probe_results.sort(key=lambda v: v[2], reverse=True)
            vectors[i] = probe_results[0]

        return vectors

    def get8Dirs(self, x, y, binary_img):
        h, w = binary_img.shape
        if not (0 <= y < h and 0 <= x < w) or binary_img[y, x] == 255:
            return [0,0,0,0,0,0,0,0]
        adjusted_vecs = self.adjust_8vectors(x, y, binary_img)
        return [vec[2] for vec in adjusted_vecs]

