import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

# 导入你提供的滑动窗口二值化类
from SlidingWindowBinarizer import SlidingWindowBinarizer


class ChineseCharImageViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.current_file_path = None  # 用于记录当前展示图片的路径
        self.initUI()

    def initUI(self):
        # 设置窗口标题，并将初始宽度增加以容纳两个面板
        self.setWindowTitle('汉字图片展示与二值化工具 (双面板对比)')
        self.resize(900, 600)

        # 创建一个垂直主布局
        main_layout = QVBoxLayout()

        # 1. 创建双面板图片展示区 (水平布局)
        images_layout = QHBoxLayout()

        # --- 左侧：原图面板 ---
        left_layout = QVBoxLayout()
        left_title = QLabel("原始图片", self)
        left_title.setAlignment(Qt.AlignCenter)
        left_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")

        self.original_image_label = QLabel('请点击下方按钮上传汉字图片', self)
        self.original_image_label.setAlignment(Qt.AlignCenter)
        self.original_image_label.setMinimumSize(400, 400)
        self.original_image_label.setStyleSheet(
            "QLabel { background-color : #f0f0f0; border: 2px dashed #aaa; font-size: 16px; color: #555; }")

        left_layout.addWidget(left_title)
        left_layout.addWidget(self.original_image_label)

        # --- 右侧：二值化结果面板 ---
        right_layout = QVBoxLayout()
        right_title = QLabel("二值化结果", self)
        right_title.setAlignment(Qt.AlignCenter)
        right_title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")

        self.binary_image_label = QLabel('等待处理...', self)
        self.binary_image_label.setAlignment(Qt.AlignCenter)
        self.binary_image_label.setMinimumSize(400, 400)
        self.binary_image_label.setStyleSheet(
            "QLabel { background-color : #f0f0f0; border: 2px dashed #aaa; font-size: 16px; color: #555; }")

        right_layout.addWidget(right_title)
        right_layout.addWidget(self.binary_image_label)

        # 将左右面板加入图片展示区
        images_layout.addLayout(left_layout)
        images_layout.addLayout(right_layout)

        # 2. 创建按钮操作区（水平布局放置两个按钮）
        btn_layout = QHBoxLayout()

        # 上传按钮
        self.upload_btn = QPushButton('上传图片', self)
        self.upload_btn.setMinimumHeight(40)
        self.upload_btn.setStyleSheet("QPushButton { font-size: 16px; font-weight: bold; }")
        self.upload_btn.clicked.connect(self.upload_image)

        # 二值化按钮 (初始状态下禁用，直到上传了图片)
        self.binarize_btn = QPushButton('二值化处理', self)
        self.binarize_btn.setMinimumHeight(40)
        self.binarize_btn.setStyleSheet("QPushButton { font-size: 16px; font-weight: bold; }")
        self.binarize_btn.setEnabled(False)
        self.binarize_btn.clicked.connect(self.process_binarization)

        # 将按钮加入水平布局
        btn_layout.addWidget(self.upload_btn)
        btn_layout.addWidget(self.binarize_btn)

        # 3. 组装主布局
        main_layout.addLayout(images_layout)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def upload_image(self):
        # 打开文件选择对话框
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择汉字图片",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
            options=options
        )

        if file_path:
            self.current_file_path = file_path  # 保存当前文件路径

            # 每次上传新图片时，重置右侧的二值化面板
            self.binary_image_label.clear()
            self.binary_image_label.setText('等待处理...')
            self.binary_image_label.setStyleSheet(
                "QLabel { background-color : #f0f0f0; border: 2px dashed #aaa; font-size: 16px; color: #555; }")

            # 使用 QPixmap 加载原图并展示在左侧面板
            pixmap = QPixmap(file_path)
            self._display_pixmap(pixmap, self.original_image_label)

            # 激活二值化按钮
            self.binarize_btn.setEnabled(True)

    def process_binarization(self):
        if not self.current_file_path:
            return

        # 优化体验：点击后暂时禁用按钮并提示正在处理
        self.binarize_btn.setEnabled(False)
        self.binarize_btn.setText("正在处理中...")
        QApplication.processEvents()  # 强制刷新UI状态

        try:
            # 1. 实例化二值化处理器并传入图片路径
            binarizer = SlidingWindowBinarizer()
            binary_array = binarizer.process_image(self.current_file_path)

            # 2. 将 Numpy 数组转换为 PyQt 可识别的 QImage
            self._cached_array = np.ascontiguousarray(binary_array)
            h, w = self._cached_array.shape
            bytes_per_line = w

            q_img = QImage(self._cached_array.data, w, h, bytes_per_line, QImage.Format_Grayscale8)

            # 3. 将 QImage 转回 QPixmap 并展示在右侧面板
            pixmap = QPixmap.fromImage(q_img)
            self._display_pixmap(pixmap, self.binary_image_label)

        except Exception as e:
            self.binary_image_label.setText(f"处理失败:\n{str(e)}")

        finally:
            # 处理结束恢复按钮状态
            self.binarize_btn.setEnabled(True)
            self.binarize_btn.setText("二值化处理")

    def _display_pixmap(self, pixmap, target_label):
        """公共方法：自适应缩放并展示图片到指定的标签(QLabel)上"""
        scaled_pixmap = pixmap.scaled(
            target_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        target_label.setPixmap(scaled_pixmap)
        target_label.setStyleSheet("QLabel { background-color : white; border: 1px solid #ccc; }")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = ChineseCharImageViewer()
    viewer.show()
    sys.exit(app.exec_())