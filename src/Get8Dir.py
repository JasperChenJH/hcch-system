import math
import numpy as np


class Stroke8DirVectorAdjust:
    def __init__(self):
        # 基础的8个方向（仅用于初始化 D0~D7）
        self.dirs = [
            (0, -1),   # D0: 上
            (1, -1),   # D1: 右上
            (1, 0),    # D2: 右
            (1, 1),    # D3: 右下
            (0, 1),    # D4: 下
            (-1, 1),   # D5: 左下
            (-1, 0),   # D6: 左
            (-1, -1)   # D7: 左上
        ]

    def _ray_cast(self, start_x: int, start_y: int, dir_x: float, dir_y: float, binary_img: np.ndarray):
        """
        核心射线探路函数（DDA算法）：
        沿任意给定方向向量 (dir_x, dir_y) 一直走，直到遇到背景(255)或越界。
        返回：
            final_dx: 实际走出的 x 位移
            final_dy: 实际走出的 y 位移
            L:        实际几何长度，即 sqrt(final_dx^2 + final_dy^2)
        """
        h, w = binary_img.shape

        if dir_x == 0 and dir_y == 0:
            return (0.0, 0.0, 0.0)

        # DDA：让每一步最多跨 1 个像素格，避免漏检像素
        steps = max(abs(dir_x), abs(dir_y))
        x_increment = dir_x / steps
        y_increment = dir_y / steps

        curr_x = float(start_x)
        curr_y = float(start_y)

        while True:
            next_x = curr_x + x_increment
            next_y = curr_y + y_increment

            grid_x = round(next_x)
            grid_y = round(next_y)

            # 越界或遇到白色背景 255，就停止
            if not (0 <= grid_y < h and 0 <= grid_x < w) or binary_img[grid_y, grid_x] == 255:
                break

            curr_x = next_x
            curr_y = next_y

        final_dx = curr_x - start_x
        final_dy = curr_y - start_y
        L = math.hypot(final_dx, final_dy)

        return (final_dx, final_dy, L)

    def adjust_vectors(self, px: int, py: int, binary_img: np.ndarray):
        """
        执行 8 方向特征提取与合向量调整。

        新规则：
        1. 先计算原始 8 个方向的向量和长度。
        2. 对每一组相邻方向 i 和 i+1：
           - 用两个原始向量相加，得到合向量方向。
           - 沿合向量方向重新 ray_cast，一直走到白色背景或越界。
           - 如果合向量探测长度 L_sum 同时大于这两个原始方向长度，
             就把 L_sum 替换给这两个方向里“原始长度更长”的那个方向。
           - 原始长度更短的那个方向不变。
        """
        h, w = binary_img.shape

        if not (0 <= py < h and 0 <= px < w) or binary_img[py, px] == 255:
            return [(0.0, 0.0, 0.0) for _ in range(8)]

        # 1. 先计算原始 8 方向
        V_origin = []
        for dx, dy in self.dirs:
            V_origin.append(self._ray_cast(px, py, dx, dy, binary_img))

        # V 是最终结果，后面只修改 V，不修改 V_origin
        V = V_origin.copy()

        # 2. 相邻方向合向量调整
        for i in range(8):
            next_i = (i + 1) % 8

            # 每次都用原始向量计算合方向
            x_curr, y_curr, L_curr = V_origin[i]
            x_next, y_next, L_next = V_origin[next_i]

            # 两个方向都没有长度，跳过
            if L_curr == 0 and L_next == 0:
                continue

            # 合向量
            sum_x = x_curr + x_next
            sum_y = y_curr + y_next

            # 合向量为 0，跳过
            if sum_x == 0 and sum_y == 0:
                continue

            # 沿合向量方向重新探测
            v_sum = self._ray_cast(px, py, sum_x, sum_y, binary_img)
            L_sum = v_sum[2]

            # 如果合方向长度大于左右两个原始长度
            if L_sum > L_curr and L_sum > L_next:
                # 替换给原始长度更长的那个方向
                if L_curr >= L_next:
                    V[i] = v_sum
                else:
                    V[next_i] = v_sum

        return V

    def get_8dir_lengths(self, px: int, py: int, binary_img: np.ndarray):
        """
        返回调整后的 8 个方向长度。
        """
        adjusted_vecs = self.adjust_vectors(px, py, binary_img)
        return [vec[2] for vec in adjusted_vecs]
