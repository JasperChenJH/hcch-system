import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import time
from PIL import Image


class SlidingWindowBinarizer:
    """
    滑动窗口投票式二值化处理器
    核心功能：基于滑动窗口+局部Gamma增强+峰值检测+投票机制的自适应二值化
    """

    def __init__(self, grid_size=(10, 10), stride=2, k=5, blur_kernel=9, blur_sigma1=75, blur_sigma2=75):
        """
        初始化二值化器参数
        :param grid_size: 网格大小，用于反推窗口尺寸
        :param stride: 滑动步长（1=逐像素滑动，越大速度越快）
        :param k: Gamma增强系数
        :param blur_kernel: 双边滤波核大小
        :param blur_sigma1: 双边滤波空间标准差
        :param blur_sigma2: 双边滤波灰度值标准差
        """
        self.grid_size = grid_size
        self.stride = stride
        self.k = k
        self.blur_kernel = blur_kernel
        self.blur_sigma1 = blur_sigma1
        self.blur_sigma2 = blur_sigma2

        # 结果存储属性
        self.original_img = None
        self.gray_img = None
        self.blurred_gray = None
        self.binary_result = None
        self.enhanced_gray = None
        self.votes_255 = None
        self.votes_0 = None
        self.uncertainty_map = None
        self.heatmap_rgb = None

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    @staticmethod
    def calculate_blur_score(image):
        """计算图像模糊度分数（拉普拉斯方差）"""
        return cv2.Laplacian(image, cv2.CV_64F).var()

    @staticmethod
    def find_simple_peaks(hist):
        """从直方图中查找简单峰值点"""
        peaks = []
        if hist[0] > hist[1]:
            peaks.append(0)
        for i in range(1, 255):
            if hist[i] > hist[i - 1] and hist[i] > hist[i + 1]:
                peaks.append(i)
        if hist[255] > hist[254]:
            peaks.append(255)
        return peaks

    def _gamma_enhance_block(self, block):
        """对局部块进行Gamma增强"""
        mean_val = np.mean(block) / 255.0
        gamma = 1.0 + self.k * (mean_val - 0.5) if mean_val > 0.5 else 1.0
        block_normalized = block.astype(np.float32) / 255.0
        enhanced_block = (np.power(block_normalized, gamma) * 255).astype(np.uint8)
        return enhanced_block

    def _estimate_global_threshold(self):
        """快速估算全局平均阈值M"""
        h, w = self.blurred_gray.shape
        win_h = h // self.grid_size[0]
        win_w = w // self.grid_size[1]

        all_Ai = []
        for r in range(0, h, win_h):
            for c in range(0, w, win_w):
                r_end = min(r + win_h, h)
                c_end = min(c + win_w, w)
                block = self.blurred_gray[r:r_end, c:c_end]

                enhanced_block = self._gamma_enhance_block(block)
                hist, _ = np.histogram(enhanced_block, bins=256, range=(0, 256))
                peaks = self.find_simple_peaks(hist)

                if len(peaks) >= 2:
                    c1, c2 = min(peaks), max(peaks)
                elif len(peaks) == 1:
                    c1 = c2 = peaks[0]
                else:
                    c1, c2 = np.min(enhanced_block), np.max(enhanced_block)

                all_Ai.append((c1 + c2) / 2.0)

        M = np.mean(all_Ai)
        print(f"\n[阶段1] 快速估算全局平均阈值 M = {M:.2f}")
        return M

    def _sliding_window_voting(self, M):
        """滑动窗口投票核心逻辑"""
        h, w = self.blurred_gray.shape
        win_h = h // self.grid_size[0]
        win_w = w // self.grid_size[1]

        # 初始化投票箱和增强图累加器
        votes_0 = np.zeros((h, w), dtype=np.int32)
        votes_255 = np.zeros((h, w), dtype=np.int32)
        enhanced_sum = np.zeros((h, w), dtype=np.float32)
        enhanced_count = np.zeros((h, w), dtype=np.int32)

        # 确定滑动坐标点（确保覆盖边缘）
        r_steps = list(range(0, h - win_h + 1, self.stride))
        if r_steps[-1] != h - win_h:
            r_steps.append(h - win_h)
        c_steps = list(range(0, w - win_w + 1, self.stride))
        if c_steps[-1] != w - win_w:
            c_steps.append(w - win_w)

        total_windows = len(r_steps) * len(c_steps)
        print(f"[阶段2] 开始滑动窗口投票... 窗口大小: {win_w}x{win_h}, 步长: {self.stride}, 总窗口数: {total_windows}")

        # 进度监控
        start_time = time.time()
        count = 0

        for r in r_steps:
            for c in c_steps:
                count += 1
                if count % (total_windows // 10 + 1) == 0:
                    print(f"  已处理 {count}/{total_windows} 个窗口...")

                # 提取当前窗口并增强
                block = self.blurred_gray[r:r + win_h, c:c + win_w]
                enhanced_block = self._gamma_enhance_block(block)

                # 累加增强图数据
                enhanced_sum[r:r + win_h, c:c + win_w] += enhanced_block
                enhanced_count[r:r + win_h, c:c + win_w] += 1

                # 直方图与寻峰
                hist, _ = np.histogram(enhanced_block, bins=256, range=(0, 256))
                peaks = self.find_simple_peaks(hist)

                if len(peaks) >= 2:
                    c1, c2 = min(peaks), max(peaks)
                elif len(peaks) == 1:
                    c1 = c2 = peaks[0]
                else:
                    c1, c2 = np.min(enhanced_block), np.max(enhanced_block)

                # 距离判定生成局部二值化结果
                if c1 > M and c2 > M:
                    binarized_block = np.full_like(block, 255, dtype=np.uint8)
                elif c1 < M and c2 < M:
                    binarized_block = np.zeros_like(block, dtype=np.uint8)
                else:
                    dist1 = np.abs(enhanced_block.astype(int) - c1)
                    dist2 = np.abs(enhanced_block.astype(int) - c2)
                    binarized_block = np.where(dist1 < dist2, 0, 255).astype(np.uint8)

                # 投票计数
                votes_255[r:r + win_h, c:c + win_w] += (binarized_block == 255)
                votes_0[r:r + win_h, c:c + win_w] += (binarized_block == 0)

        print(f"滑动窗口处理完毕！耗时: {time.time() - start_time:.2f} 秒")

        # 生成最终结果
        final_binary = np.where(votes_255 > votes_0, 255, 0).astype(np.uint8)
        safe_count = np.maximum(enhanced_count, 1)
        final_enhanced = (enhanced_sum / safe_count).astype(np.uint8)

        return final_binary, final_enhanced, votes_255, votes_0

    def _generate_uncertainty_heatmap(self):
        """生成投票分歧热力图"""
        total_votes = self.votes_255 + self.votes_0
        total_votes[total_votes == 0] = 1  # 防止除零
        uncertainty = 1.0 - (np.abs(self.votes_255 - self.votes_0) / total_votes)
        self.uncertainty_map = (uncertainty * 255).astype(np.uint8)

        # 生成彩色热力图
        heatmap_img = cv2.applyColorMap(self.uncertainty_map, cv2.COLORMAP_JET)
        self.heatmap_rgb = cv2.cvtColor(heatmap_img, cv2.COLOR_BGR2RGB)

    def process_image(self, image_path):
        """
        处理指定路径的图像，执行完整的二值化流程
        :param image_path: 图像文件路径
        :return: 二值化结果图像
        """
        # 1. 加载图像
        print(f"尝试加载图像: {image_path}")
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f'错误：文件 {image_path} 不存在，请检查图片路径是否正确。')
        
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f'错误：{image_path} 不是一个文件，请检查路径是否正确。')
        
        # 尝试使用 PIL 库读取图像，解决 Unicode 路径问题
        try:
            # 使用 PIL 读取图像
            pil_image = Image.open(image_path)
            # 转换为 OpenCV 格式
            self.original_img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            if self.original_img is None:
                raise Exception(f'错误：无法读取图像文件 {image_path}，可能是文件格式不支持或文件损坏。')
            
            self.gray_img = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2GRAY)
            print(f"成功加载图像: {image_path}")
        except Exception as e:
            print(f"加载图像时出错: {str(e)}")
            raise

        # 2. 双边滤波降噪
        self.blurred_gray = cv2.bilateralFilter(
            self.gray_img,
            self.blur_kernel,
            self.blur_sigma1,
            self.blur_sigma2
        )
        print("已应用 双边滤波降噪。")

        # 3. 估算全局阈值
        M = self._estimate_global_threshold()

        # 4. 滑动窗口投票
        self.binary_result, self.enhanced_gray, self.votes_255, self.votes_0 = self._sliding_window_voting(M)

        # 5. 生成不确定性热力图
        self._generate_uncertainty_heatmap()

        return self.binary_result

    def show_results(self):
        """显示处理结果可视化面板"""
        if self.original_img is None:
            raise RuntimeError("请先调用process_image()处理图像")

        plt.figure(figsize=(12, 10))
        plt.subplot(221), plt.imshow(cv2.cvtColor(self.original_img, cv2.COLOR_BGR2RGB)), plt.title('原始图像')
        plt.subplot(222), plt.imshow(self.enhanced_gray, cmap='gray'), plt.title('滑动平均Gamma增强图')
        plt.subplot(223), plt.imshow(self.binary_result, cmap='gray'), plt.title('多数投票决出结果 (纯净版)')
        plt.subplot(224), plt.imshow(self.heatmap_rgb), plt.title('投票分歧热力图(越红说明局部越模糊)')
        plt.tight_layout()
        plt.show()

    def save_result(self, save_path='binary_voting_result.jpg'):
        """
        保存二值化结果
        :param save_path: 保存路径
        """
        if self.binary_result is None:
            raise RuntimeError("请先调用process_image()处理图像")

        cv2.imwrite(save_path, self.binary_result)
        print(f'\n处理完成！最终二值化结果已保存至: {save_path}')

