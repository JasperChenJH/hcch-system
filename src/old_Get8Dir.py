import math
import numpy as np


class Stroke8DirVectorAdjust:
    def __init__(self):
        # 基础的8个方向（仅用于初始化 D0~D7）
        self.dirs = [
            (0, -1),  # D0: 上
            (1, -1),  # D1: 右上
            (1, 0),  # D2: 右
            (1, 1),  # D3: 右下
            (0, 1),  # D4: 下
            (-1, 1),  # D5: 左下
            (-1, 0),  # D6: 左
            (-1, -1)  # D7: 左上
        ]

    def _ray_cast(self, start_x: int, start_y: int, dir_x: float, dir_y: float, binary_img: np.ndarray):
        """
        核心射线探路函数 (DDA算法)：
        沿任意给定的方向向量 (dir_x, dir_y) 发射线，直到遇到背景(255)或越界。
        返回 (实际走出的x位移, 实际走出的y位移, 真实的几何欧氏距离L)
        """
        h, w = binary_img.shape

        # 如果方向向量为零，直接返回
        if dir_x == 0 and dir_y == 0:
            return (0.0, 0.0, 0.0)

        # DDA 步长设定：取 x 和 y 中较大的那个绝对值作为细分的步数，
        # 确保我们在网格中每一步最多只跨越 1 个像素格子，不会漏掉中间的像素。
        steps = max(abs(dir_x), abs(dir_y))
        x_increment = dir_x / steps
        y_increment = dir_y / steps

        # 使用浮点数记录当前射线到达的精确位置
        curr_x = float(start_x)
        curr_y = float(start_y)

        while True:
            # 向前步进一点点
            next_x = curr_x + x_increment
            next_y = curr_y + y_increment

            # 将精确坐标四舍五入，映射到离散的二维矩阵网格索引上
            grid_x = round(next_x)
            grid_y = round(next_y)

            # 停止条件：超出图像边界，或者该像素点为 255 (背景)
            if not (0 <= grid_y < h and 0 <= grid_x < w) or binary_img[grid_y, grid_x] == 255:
                break

            # 更新当前位置
            curr_x = next_x
            curr_y = next_y

        # 走到终点后，计算真正的相对位移
        final_dx = curr_x - start_x
        final_dy = curr_y - start_y

        # 计算真实的几何直线长度（欧氏距离），代替之前单纯的像素计数
        L = math.hypot(final_dx, final_dy)

        return (final_dx, final_dy, L)

    def adjust_vectors(self, px: int, py: int, binary_img: np.ndarray, sync_update: bool = True):
        """执行特征提取主流程"""
        h, w = binary_img.shape

        # 如果起点不合法或本身就是背景(255)，返回0向量
        if not (0 <= py < h and 0 <= px < w) or binary_img[py, px] == 255:
            return [(0.0, 0.0, 0.0) for _ in range(8)]

        # ================= 1. 初始 8 方向探路 =================
        V = []
        for dx, dy in self.dirs:
            # 初始探路也使用射线法，以保证得到的 L 也是真实的欧氏距离
            vec = self._ray_cast(px, py, dx, dy, binary_img)
            V.append(vec)

        # 保存探路初始状态的副本，用于获取 i+1 的原始值
        V_ref = V.copy() if sync_update else V

        # ================= 2. 向量相加，重新探路并比较 =================
        for i in range(8):
            v_curr = V[i]

            # 拦截逻辑：如果初始探路时该方向长度已经是0，则跳过
            if v_curr[2] == 0:
                continue

            # 获取顺时针相邻的 i+1 方向
            v_next = V_ref[(i + 1) % 8]

            x_curr, y_curr, L_curr = v_curr
            x_next, y_next, L_next = v_next

            # 计算合向量 (第 i 方向 + 第 i+1 方向)
            sum_x = x_curr + x_next
            sum_y = y_curr + y_next

            # 如果合向量为零向量，跳过
            if sum_x == 0 and sum_y == 0:
                continue

            # 按新的合向量方向进行射线探路，获取真实的探路结果和长度 L_sum
            v_sum = self._ray_cast(px, py, sum_x, sum_y, binary_img)
            L_sum = v_sum[2]

            # 核心替换逻辑：如果合向量探测的长度 大于 i 方向本身的长度 且 大于 i+1 方向的长度
            if L_sum > L_curr and L_sum > L_next:
                V[i] = v_sum  # 使用合向量探测结果替换第 i 个方向

        return V

    def get_8dir_lengths(self, px: int, py: int, binary_img: np.ndarray, sync_update: bool = True):
        """
        辅助方法：提取调整后的 8个方向长度 L 构成的特征向量
        """
        adjusted_vecs = self.adjust_vectors(px, py, binary_img, sync_update)
        return [vec[2] for vec in adjusted_vecs]