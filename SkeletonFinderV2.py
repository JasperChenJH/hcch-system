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

    def is_skeleton_point(self, features, abs_tol=0, rel_tol=0,
                          use_cosine3d=True, cosine_thresh=1 ,length_diff_thresh=0):
        # length_diff_thresh 就是你要的：对应点长度差绝对值最大允许值
        if len(features) != 8:
            return False

        # 8方向索引固定：0上 1右上 2右 3右下 4下 5左下 6左 7左上
        lines = [features[i] + features[i + 4] for i in range(4)]
        max_line_len = max(lines)
        main_axis_idx = lines.index(max_line_len)

        other_lines = [lines[i] for i in range(4) if i != main_axis_idx]
        if max_line_len <= 1.5 * max(other_lines):
            return False

        # ====================== 严格轴对称向量顺序 ======================
        if main_axis_idx == 0:  # 主轴：上下轴 (0上-4下)
            A = [7, 6, 5]  # 左上、左、左下
            B = [1, 2, 3]  # 右上、右、右下

        elif main_axis_idx == 1:  # 主轴：右上-左下 (1-5)
            A = [7, 0, 4]  # 左上、上、下
            B = [2, 3, 6]  # 右、右下、左

        elif main_axis_idx == 2:  # 主轴：左右轴 (2右-6左)
            A = [7, 0, 1]  # 左上、上、右上
            B = [5, 4, 3]  # 左下、下、右下

        elif main_axis_idx == 3:  # 主轴：右下-左上 (3-7)
            A = [0, 1, 2]  # 上、右上、右
            B = [4, 5, 6]  # 下、左下、左

        else:
            return False

        # 生成轴对称向量
        A = [features[i] for i in A]
        B = [features[i] for i in B]

        if use_cosine3d:
            normA = np.linalg.norm(A)
            normB = np.linalg.norm(B)
            if normA < 1e-6 or normB < 1e-6:
                return False

            # 1. 先判断余弦相似度
            cos_sim = abs(np.dot(A, B) / (normA * normB))
            if cos_sim < cosine_thresh:
                return False

            # ============== 你要的核心逻辑：对应点长度差判断 ==============
            # 2. 再检查每一对对应位置的长度差绝对值都 < 阈值
            for a_val, b_val in zip(A, B):
                if abs(a_val - b_val) > length_diff_thresh:
                    return False

            # 两个条件都满足才是骨架点
            return True

        else:
            for a, b in zip(A, B):
                diff = abs(a - b)
                max_v = max(a, b)
                if diff > abs_tol and (max_v == 0 or diff / max_v > rel_tol):
                    return False
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
    test_image = "G:\\py_workplace\\HanziKeypoint\\img.png"

    if os.path.exists(test_image):
        finder.find_and_visualize(test_image)
    else:
        print(f"错误：未找到图片 {test_image}")