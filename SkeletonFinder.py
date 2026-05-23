import cv2
import numpy as np
import os
from SlidingWindowBinarizer import SlidingWindowBinarizer


class HanziSkeletonFinder:
    def __init__(self, grid_size=(10, 10), stride=2):
        # 初始化二值化器
        self.binarizer = SlidingWindowBinarizer(grid_size=grid_size, stride=stride)

    def get_8dirs_features(self, x, y, binary_img):
        """提取某个像素点在8个方向上的黑色像素连续长度"""
        h, w = binary_img.shape
        # 方向定义: 0:上, 1:右上, 2:右, 3:右下, 4:下, 5:左下, 6:左, 7:左上
        dirs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
        features = []
        for dy, dx in dirs:
            cy, cx, cnt = y, x, 0
            while True:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and binary_img[ny, nx] == 0:
                    cy, cx = ny, nx
                    cnt += 1
                else:
                    break
            features.append(cnt)
        return features

    def is_skeleton_point(self, features, abs_tol=0, rel_tol=0):
        """
        骨架点核心判定逻辑（修正版）：
        1. 8个方向两两相加，合成4条贯穿该点的线段。
        2. 找到最长的线段作为主轴。
        3. 主轴长度需大于其余3条合成线段中任意一条的 1.5 倍。
        4. 以主轴为对称轴，检查两侧射线对折后是否在容差范围内重合。
        """
        if len(features) != 8:
            return False

        # --- 步骤 1: 8个方向两两相加，合成 4 条线 ---
        # lines[0] = 上+下, lines[1] = 右上+左下, lines[2] = 右+左, lines[3] = 右下+左上
        lines = []
        for i in range(4):
            lines.append(features[i] + features[i + 4])

        # --- 步骤 2: 找到最长线（主轴）及其索引 ---
        max_line_len = max(lines)
        main_axis_idx = lines.index(max_line_len)

        # --- 步骤 3: 1.5 倍判定 (将主轴与其余 3 条合成线比较) ---
        # 提取出除了主轴之外的另外 3 条线的长度
        other_lines = [lines[i] for i in range(4) if i != main_axis_idx]
        max_other_line_len = max(other_lines)

        # 如果最长的线，没有达到其他任意贯穿线最大值的 1.5 倍，说明不是骨架点
        if max_line_len <= 1.5 * max_other_line_len:
            return False

        # --- 步骤 4: 宽容对称判定 (对折重合) ---
        # 比如 main_axis=0 (上和下是主轴)，那么关于它对称的射线对是:
        # (1, 7) 即 右上 和 左上
        # (2, 6) 即 右 和 左
        # (3, 5) 即 右下 和 左下
        test_pairs = [
            ((main_axis_idx + 1) % 8, (main_axis_idx + 7) % 8),
            ((main_axis_idx + 2) % 8, (main_axis_idx + 6) % 8),
            ((main_axis_idx + 3) % 8, (main_axis_idx + 5) % 8)
        ]

        for p1, p2 in test_pairs:
            l1, l2 = features[p1], features[p2]
            diff = abs(l1 - l2)
            max_v = max(l1, l2)

            # 容差判定：绝对误差（如差2像素内）或相对误差（如相差不超过30%）
            if diff > abs_tol:
                if max_v == 0 or (diff / max_v) > rel_tol:
                    return False  # 有一对不对称，则不是骨架点

        return True

    def find_and_visualize(self, image_path):
        print(f"正在进行自适应二值化: {image_path}...")
        binary_img = self.binarizer.process_image(image_path)

        h, w = binary_img.shape
        result_img = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2BGR)

        print("正在提取骨架点，请稍候...")
        skeleton_count = 0

        for y in range(0, h):
            for x in range(0, w):
                if binary_img[y, x] == 0:
                    feats = self.get_8dirs_features(x, y, binary_img)

                    if self.is_skeleton_point(feats):
                        cv2.circle(result_img, (x, y), 1, (0, 0, 255), -1)
                        skeleton_count += 1

        print(f"识别完成！共找到 {skeleton_count} 个骨架点。")

        cv2.imshow("Original Binary", binary_img)
        cv2.imshow("Skeleton Points (Red)", result_img)

        save_name = "skeleton_result_v2.png"
        cv2.imwrite(save_name, result_img)
        print(f"结果已保存至: {save_name}")

        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    finder = HanziSkeletonFinder(grid_size=(10, 10), stride=2)
    test_image = "G:\\py_workplace\\HanziKeypoint\\意.png"

    if os.path.exists(test_image):
        finder.find_and_visualize(test_image)
    else:
        print(f"错误：未找到图片 {test_image}")