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

    def is_endpoint(self, dir_list):
        """
        根据自定义规则判定是否为端点：
        1. 有一最长距离是其对应距离（dir_list中相对位置-4或+4）的2倍以上
        2. 对应距离左右两侧距离的长度差很小（+ — 1），且大于对应距离（如果对应距离为0，则进行拉普拉斯校准）
        3. 对应距离左右两侧距离小于对应距离2倍
        4. 剩下七个值和平均值之间的差的绝对值都要小于某一阈值 (新增严格限制)
        5. 与最长距离相对的距离应大于某阈值，且？}
        :param dir_list: 包含8个方向长度的列表
        :return: bool, 是否为端点
        """
        # 如果全为0，说明可能是孤立噪点或者计算异常
        if all(v == 0 for v in dir_list):
            return False

        # 找到最长距离
        max_len = max(dir_list)
        max_idx = dir_list.index(max_len)
        min_len = min(dir_list)

        # 满足“有一距离很长”
        # if max_len < self.long_threshold:
        #    return False

        ## 提取剩下的 7 个距离 (对列表排序后去掉最后一个最大值)
        # sorted_list = sorted(dir_list)
        # remaining_7 = sorted_list[:-1]

        # 提取最长距离（margin，边距）对应的边距及其两侧的边距 ***
        sorted_list = sorted(dir_list)
        len_l_1 = dir_list[(max_idx - 1) % 8]
        len_l_2 = dir_list[(max_idx - 2) % 8]
        len_l_3 = dir_list[(max_idx - 3) % 8]
        opposite_len = dir_list[(max_idx + 4) % 8]
        len_r_1 = dir_list[(max_idx + 1) % 8]
        len_r_2 = dir_list[(max_idx + 2) % 8]
        len_r_3 = dir_list[(max_idx + 3) % 8]

        print(dir_list, max_idx)

        # 对应边距与两侧边距的差较小，大于0，小于等于2 ***
        margin_equal = all(abs(a - b) <= 2 for a, b in [
            (len_l_1, len_r_1),
            (len_l_2, len_r_2),
            (len_l_3, len_r_3)
        ])

        # 条件判定：最长距离 >= 对应距离的 2 倍，
        if max_len >= (2 * opposite_len) and margin_equal and opposite_len <= 5:  # ***
            print(dir_list)
            return True

        return False

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
                if self.is_endpoint(dir_list):
                    # print(dir_list) # 若嫌输出太多可注释掉
                    endpoints_x.append(i)
                    endpoints_y.append(j)

        print(f"端点提取完成！共找到 {len(endpoints_x)} 个端点像素，耗时: {time.time() - start_time:.2f} 秒")

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