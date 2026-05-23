from SlidingWindowBinarizer import SlidingWindowBinarizer
from new.Get8Dir import Stroke8DirVectorAdjust
import openpyxl  # 用于操作Excel

def find_and_visualize(image_path, excel_save_path="binary_image_data.xlsx"):
    adjust = Stroke8DirVectorAdjust()
    print(f"正在进行自适应二值化: {image_path}...")

    # 二值化处理
    binary = SlidingWindowBinarizer()
    binary_img = binary.process_image(image_path)
    h, w = binary_img.shape
    print(f"二值化结果大小: {h}x{w}")
    print("二值化图像矩阵预览：")
    print(binary_img)

    # 创建Excel工作簿和工作表
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "8方向向量数据"

    # 建议先循环行(j)，再循环列(i)，读取速度更快
    for j in range(h):
        for i in range(w):
            if binary_img[j, i] == 255:
                continue
            dir_list = adjust.get_8dir_lengths(i, j, binary_img)
            # 【关键修改 2】把浮点数保留2位小数，让Excel数据清爽易读
            rounded_list = [round(v, 2) for v in dir_list]
            # 判断列表是否全为0
            if not all(v == 0 for v in rounded_list):
                # 写入 Excel
                ws.cell(row=j + 1, column=i + 1, value=str(rounded_list))

    # 保存Excel文件
    wb.save(excel_save_path)
    print(f"数据已保存到Excel文件: {excel_save_path}")

# 运行
path = "./拐.png"
find_and_visualize(path)