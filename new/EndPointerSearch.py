import cv2
import numpy as np
import matplotlib.pyplot as plt
import time

# 导入你的二值化类和8方向计算类
from SlidingWindowBinarizer import SlidingWindowBinarizer
from new.Get8Dir import Stroke8DirVectorAdjust


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
        1. 有一距离很长
        2. 其他距离长度的方差很小
        3. 这一最长距离是其他距离的平均的两倍及以上
        4. 剩下七个值和平均值之间的差的绝对值都要小于某一阈值 (新增严格限制)
        :param dir_list: 包含8个方向长度的列表
        :return: bool, 是否为端点
        """
        # 如果全为0，说明可能是孤立噪点或者计算异常
        if all(v == 0 for v in dir_list):
            return False

        # 找到最长距离
        max_len = max(dir_list)

        # 满足“有一距离很长”
        if max_len < self.long_threshold:
            return False

        # 提取剩下的 7 个距离 (对列表排序后去掉最后一个最大值)
        sorted_list = sorted(dir_list)
        remaining_7 = sorted_list[:-1]

        # 计算剩下 7 个距离的方差和平均值
        variance = np.var(remaining_7)
        mean_val = np.mean(remaining_7)
        # 计算最长距离
        max_val = np.max(remaining_7)
        min_val = np.min(remaining_7)
        # 【优化你新增的条件】：使用 all() 替代全局变量 flag 和 for 循环
        # 最长点的对应点和对应点的左右两个点的长度形成一个列表
        opposite_three = get_opposite_and_neighbors(dir_list)
        opposite_three_mean = np.mean(opposite_three)
        opposite_three_max = np.max(opposite_three)
        # 意思是：剩下的7个值中，是否"所有"的值都满足 abs(x - mean_val) <= self.var_threshold
        # is_dev_small = all(abs(x - mean_val) <= self.abs_threshold for x in remaining_7)
        is_dev_small = all(abs(x - opposite_three_mean) <= self.abs_threshold for x in opposite_three)

        # 条件判定：方差很小 且 最长距离 >= 其他距离平均值的 2 倍 且 满足绝对差限制
        # flag = variance <= self.var_threshold
        if  max_len >= (2 * opposite_three_max) and is_dev_small and opposite_three[1]>=3 and opposite_three[1]<=5:
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
                rounded_list = [round(v, 2) for v in dir_list]
                print("非255点坐标:", i, j, "像素值:", binary_img[j, i], "8方向:", rounded_list)
                # 进行端点判定
                if self.is_endpoint(rounded_list):
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

def get_opposite_and_neighbors(dir_list):
    """
    找到最长方向的对应方向，以及对应方向左右两个方向的长度
    :param dir_list: 8个方向长度列表
    :return: [左邻方向长度, 对应方向长度, 右邻方向长度]
    """
    max_idx = np.argmax(dir_list)

    # 最长方向的对应方向，也就是相反方向
    opposite_idx = (max_idx + 4) % 8

    # 对应方向的左右两个方向
    left_idx = (opposite_idx - 1) % 8
    right_idx = (opposite_idx + 1) % 8

    return [
        dir_list[left_idx],
        dir_list[opposite_idx],
        dir_list[right_idx]
    ]

if __name__ == '__main__':
    # 运行测试
    image_path = "./白.png"  # 替换为你的图片路径

    # 实例化端点检测器，参数可以根据图片的实际分辨率调整
    # long_threshold: 要求最长距离至少达到这个像素值
    # var_threshold: 剩余7个距离的方差上限，越小要求越严苛（越均匀）
    detector = StrokeEndpointDetector(long_threshold=0, var_threshold=14,abs_threshold = 3)
    detector.detect_and_visualize(image_path)