import cv2
import numpy as np
import pandas as pd
import os
from SlidingWindowBinarizer import SlidingWindowBinarizer

class HanziDataTool:
    def __init__(self, save_path='train_set_v2.xlsx'):
        self.save_path = save_path
        self.binarizer = SlidingWindowBinarizer(grid_size=(10, 10), stride=2)

        # 交互状态
        self.drawing = False
        self.ix, self.iy = -1, -1
        self.current_box = None
        self.boxes = []  # 存储当前图片的标注框 [(x1, y1, x2, y2, label), ...]

    def get_8dirs_features(self, x, y, binary_img):
        """复用你的8方向探测逻辑"""
        h, w = binary_img.shape
        # 这里的 binary_img 应该是背景为255，笔画为0的图
        dirs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
        features = []
        for dy, dx in dirs:
            cy, cx, cnt = y, x, 0
            while 0 <= cy + dy < h and 0 <= cx + dx < w and binary_img[cy + dy, cx + dx] == 0:
                cy += dy
                cx += dx
                cnt += 1
            features.append(cnt)
        return features

    def mouse_callback(self, event, x, y, flags, param):
        """处理鼠标框选逻辑"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix, self.iy = x, y

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.current_box = (self.ix, self.iy, x, y)

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            # 记录框（确保坐标顺序）
            x1, x2 = min(self.ix, x), max(self.ix, x)
            y1, y2 = min(self.iy, y), max(self.iy, y)
            self.boxes.append((x1, y1, x2, y2))
            self.current_box = None

    def process_and_label(self, image_path, label_type=1):
        """
        核心流程：二值化 -> 框选 -> 提取特征 -> 保存
        :param label_type: 1:端点, 2:拐点, 3:交汇, 4:交叉
        """
        # 1. 使用你上传的算法进行二值化
        self.binarizer.process_image(image_path)
        binary_img = self.binarizer.binary_result  # 假设 0 是笔画，255 是背景

        display_img = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2BGR)
        win_name = "Labeling - Press 'S' to Save, 'C' to Clear, 'Q' to Quit"
        cv2.namedWindow(win_name)
        cv2.setMouseCallback(win_name, self.mouse_callback)

        print(f"--- 正在处理: {image_path} ---")
        print("操作指南: 鼠标拖动框选端点区域。'S'保存并进入下一张, 'C'清空当前框, 'Q'退出")

        while True:
            temp_img = display_img.copy()
            # 画已经定好的框
            for box in self.boxes:
                cv2.rectangle(temp_img, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
            # 画正在拖动的框
            if self.current_box:
                cv2.rectangle(temp_img, (self.current_box[0], self.current_box[1]),
                              (self.current_box[2], self.current_box[3]), (0, 0, 255), 1)

            cv2.imshow(win_name, temp_img)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('s'):  # 保存数据
                self.save_data_from_boxes(binary_img, label_type)
                self.boxes = []
                break
            elif key == ord('c'):  # 清空
                self.boxes = []
            elif key == ord('q'):  # 退出
                cv2.destroyAllWindows()
                return False

        return True

    def save_data_from_boxes(self, binary_img, label_value):
        """解析所有框，提取框内所有黑像素的特征"""
        all_features = []

        for (x1, y1, x2, y2) in self.boxes:
            # 在二值图中遍历这个矩形区域
            for ty in range(y1, y2 + 1):
                for tx in range(x1, x2 + 1):
                    # 如果该像素是笔画（黑色）
                    if binary_img[ty, tx] == 0:
                        feat = self.get_8dirs_features(tx, ty, binary_img)
                        all_features.append(feat + [label_value])

        if all_features:
            df_new = pd.DataFrame(all_features, columns=[f'方向{i}' for i in range(1, 9)] + ['类标号'])

            # 追加保存到 Excel
            if os.path.exists(self.save_path):
                df_old = pd.read_excel(self.save_path)
                df_final = pd.concat([df_old, df_new], ignore_index=True)
            else:
                df_final = df_new

            df_final.to_excel(self.save_path, index=False)
            print(f"Successfully saved {len(all_features)} points to {self.save_path}")


# ================= 使用示例 =================
if __name__ == "__main__":
    tool = HanziDataTool(save_path='my_new_dataset.xlsx')

    # 假设你有一个包含图片的文件夹
    img_list = ["G:\py_workplace\HanziKeypoint\训练图片"]  # 这里替换成你的图片路径列表

    # 处理目录，获取所有图像文件
    processed_paths = []
    for path in img_list:
        if os.path.isdir(path):
            # 遍历目录中的所有文件
            for filename in os.listdir(path):
                # 检查文件扩展名是否为图像格式
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                    processed_paths.append(os.path.join(path, filename))
        else:
            # 如果是文件，直接添加
            processed_paths.append(path)

    print(f"找到 {len(processed_paths)} 个图像文件")
    for img_p in processed_paths:
        print(f"处理: {img_p}")
        if not tool.process_and_label(img_p, label_type=1):  # 1代表端点
            break