import cv2
import numpy as np
import matplotlib.pyplot as plt
import time
import matplotlib

# 导入你的二值化类和8方向计算类
from SlidingWindowBinarizer import SlidingWindowBinarizer
from new.Get8Dir import Stroke8DirVectorAdjust
matplotlib.use('TkAgg')  # 强制切换后端，解决报错

class StrokeEndpointDetector:
    def __init__(self, long_threshold=20.0, var_threshold=2.0, abs_threshold = 0.5):
        """
        初始化端点检测器
        :param long_threshold: 判定为“很长”的最小长度阈值
        :param var_threshold: 判定“其他距离方差很小”的方差阈值
        :param abs_threshold: 七个值和平均值之间的差的绝对值都要小于某一阈值
        """
        self.long_threshold = long_threshold
        self.var_threshold = var_threshold
        self.abs_threshold = abs_threshold
        self.binarizer = SlidingWindowBinarizer()
        self.adjust = Stroke8DirVectorAdjust()

        # 设置中文字体以便绘图显示
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False

    def is_corner(self, dir_list):
        """
        拐点判定函数：长方向数量必须恰好为 2

        判断条件：
        1. 8 个方向不能全为 0；
        2. 找出所有长度 >= long_threshold 的长方向；
        3. 长方向数量必须恰好为 2；
        4. 两个长方向不能相邻；
        5. 两个长方向不能相反；
        6. 两个长方向的 circular_distance 必须是 2 或 3；
        7. 两个长方向之间夹着的方向必须足够短；
        8. 两个长方向之间夹着的短方向，要和对应反方向之间夹着的短方向长度接近。
        """

        if all(v == 0 for v in dir_list):
            return False

        long_threshold = 15
        base_short_threshold = 0.5 * long_threshold

        # 中间短方向对称性阈值
        # 例如两个值差值 <= 3，认为接近相等
        middle_equal_threshold = 3.0

        # 1. 找出所有长方向
        long_dir_indices = []
        for dir_idx in range(8):
            if dir_list[dir_idx] >= long_threshold:
                long_dir_indices.append(dir_idx)

        # 2. 长方向数量必须恰好为 2
        if len(long_dir_indices) != 2:
            return False

        # 3. 取出这两个长方向
        idx1, idx2 = long_dir_indices

        # 4. 计算两个长方向在 8 方向环上的最短距离
        raw_distance = abs(idx1 - idx2)
        circular_distance = min(raw_distance, 8 - raw_distance)

        min_long_len = min(dir_list[idx1], dir_list[idx2])

        # 两个长方向相邻，不算拐点
        if circular_distance == 1:
            return False

        # 两个长方向相反，更像直线笔画，不算普通拐点
        if circular_distance == 4:
            return False

        # circular_distance = 2：典型 L 型拐点
        if circular_distance == 2:
            dynamic_short_threshold = min(
                base_short_threshold,
                min_long_len * 0.35
            )

        # circular_distance = 3：较宽角度候选，容易误判，所以更严格
        elif circular_distance == 3:
            dynamic_short_threshold = min(
                base_short_threshold,
                min_long_len * 0.1
            )

        else:
            return False

        # 5. 获取两个长方向之间较短路径上的中间方向
        middle_indices = self.get_middle_dirs(idx1, idx2)

        # 6. 两个长方向之间夹着的方向必须足够短
        for mid_idx in middle_indices:
            if dir_list[mid_idx] > dynamic_short_threshold:
                return False

        # 7. 新增条件：
        # 两个长方向之间夹着的短方向，
        # 要和两个长方向的反方向之间夹着的短方向长度接近
        opposite_idx1 = (idx1 + 4) % 8
        opposite_idx2 = (idx2 + 4) % 8

        opposite_middle_indices = self.get_middle_dirs(opposite_idx1, opposite_idx2)

        # 正常情况下，circular_distance = 2 时两边各夹 1 个方向；
        # circular_distance = 3 时两边各夹 2 个方向。
        # 如果数量不一致，直接排除。
        if len(middle_indices) != len(opposite_middle_indices):
            return False

        # 对应位置的短方向长度要接近
        for mid_idx, opp_mid_idx in zip(middle_indices, opposite_middle_indices):
            if abs(dir_list[mid_idx] - dir_list[opp_mid_idx]) > middle_equal_threshold:
                return False

        return True

    def get_middle_dirs(self,idx1, idx2):
        """
        获取两个方向在8方向环上较短路径之间的中间方向
        """
        clockwise = []
        cur = (idx1 + 1) % 8
        while cur != idx2:
            clockwise.append(cur)
            cur = (cur + 1) % 8

        counter_clockwise = []
        cur = (idx2 + 1) % 8
        while cur != idx1:
            counter_clockwise.append(cur)
            cur = (cur + 1) % 8

        if len(clockwise) <= len(counter_clockwise):
            return clockwise
        else:
            return counter_clockwise

    def detect_and_visualize(self, image_path):
        """
        完整流程：加载图像 -> 二值化 -> 8方向提取 -> 端点判定 -> 可视化
        """
        print(f"开始处理图像: {image_path}")

        # 1. 图像二值化
        print(">> 正在执行二值化处理...")
        binary_img = self.binarizer.process_image(image_path)
        h, w = binary_img.shape

        # 2. 准备端点列表
        endpoints_x = []
        endpoints_y = []

        print(f">> 正在进行8方向计算和端点判定 (尺寸: {w}x{h})...")
        start_time = time.time()

        # 3. 遍历像素进行判定
        for j in range(h):
            for i in range(w):
                # 假设 255 是背景，0 是笔画。我们只检测笔画上的点
                if binary_img[j, i] == 255:
                    continue

                # 获取该点的8方向长度
                dir_list = self.adjust.get_8dir_lengths(i, j, binary_img)

                # 进行端点判定
                if self.is_corner(dir_list):
                    # print(dir_list) # 若嫌输出太多可注释掉
                    endpoints_x.append(i)
                    endpoints_y.append(j)

        print(f"提取完成！共找到 {len(endpoints_x)} 个端点像素，耗时: {time.time() - start_time:.2f} 秒")

        # 4. 结果可视化
        self._show_result(image_path, binary_img, endpoints_x, endpoints_y)

    def _show_result(self, image_path, binary_img, pts_x, pts_y):
        """
        可视化展示结果
        """
        # 读取原图用于展示
        original_img = cv2.imread(image_path)
        if original_img is not None:
            original_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
        else:
            # 如果 cv2 读不到（如路径含中文），用 PIL 曲线救国
            from PIL import Image
            original_img = np.array(Image.open(image_path))

        # 将二值化图转为彩色，方便在上面画红点
        binary_rgb = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2RGB)

        # 在原图和二值化图上画红点
        # plt 散点图可以直接覆盖上去，这里主要是为了生成可视化面板
        plt.figure(figsize=(14, 6))

        # 子图1：原图 + 端点标记
        plt.subplot(1, 2, 1)
        plt.imshow(original_img)
        plt.scatter(pts_x, pts_y, c='red', s=10, label='检测到的端点')
        plt.title('原图与端点标记')
        plt.axis('off')
        plt.legend()

        # 子图2：二值化图 + 端点标记
        plt.subplot(1, 2, 2)
        plt.imshow(binary_img, cmap='gray')
        plt.scatter(pts_x, pts_y, c='red', s=10, label='检测到的端点')
        plt.title('二值化图与端点标记')
        plt.axis('off')
        plt.legend()

        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    # 运行测试
    image_path = "./鼎.png"  # 替换为你的图片路径

    # 实例化端点检测器，参数可以根据图片的实际分辨率调整
    # long_threshold: 要求最长距离至少达到这个像素值
    # var_threshold: 剩余7个距离的方差上限，越小要求越严苛（越均匀）
    detector = StrokeEndpointDetector(long_threshold=0, var_threshold=14,abs_threshold = 5)
    detector.detect_and_visualize(image_path)