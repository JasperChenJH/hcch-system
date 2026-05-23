import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import time
# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def calculate_blur_score(image):
    return cv2.Laplacian(image, cv2.CV_64F).var()


def find_simple_peaks(hist):
    peaks = []
    if hist[0] > hist[1]:
        peaks.append(0)
    for i in range(1, 255):
        if hist[i] > hist[i - 1] and hist[i] > hist[i + 1]:
            peaks.append(i)
    if hist[255] > hist[254]:
        peaks.append(255)
    return peaks


def sliding_window_voting_binarization(gray_img, grid_size=(10, 10), stride=2, k=0):
    """
    滑动窗口(卷积式) + 投票决定的二值化处理

    参数 stride: 步长。设为 1 即“一步一步走”，若图片较大建议设为 2~4 提速。
    """
    h, w = gray_img.shape
    # 根据用户习惯的 grid_size 反推窗口大小
    win_h = h // grid_size[0]
    win_w = w // grid_size[1]

    # --- 第一遍：快速估算全局阈值 M ---
    # 为了防止滑动窗口重复计算拖慢几百倍速度，M的估算依然采用不重叠跳跃采样
    all_Ai = []
    for r in range(0, h, win_h):
        for c in range(0, w, win_w):
            r_end = min(r + win_h, h)
            c_end = min(c + win_w, w)
            block = gray_img[r:r_end, c:c_end]

            mean_val = np.mean(block) / 255.0
            gamma = 1.0 + k * (mean_val - 0.5) if mean_val > 0.5 else 1.0

            block_normalized = block.astype(np.float32) / 255.0
            enhanced_block = (np.power(block_normalized, gamma) * 255).astype(np.uint8)

            hist, _ = np.histogram(enhanced_block, bins=256, range=(0, 256))
            peaks = find_simple_peaks(hist)

            if len(peaks) >= 2:
                c1, c2 = min(peaks), max(peaks)
            elif len(peaks) == 1:
                c1 = c2 = peaks[0]
            else:
                c1, c2 = np.min(enhanced_block), np.max(enhanced_block)

            all_Ai.append((c1 + c2) / 2.0)

    M = np.mean(all_Ai)
    print(f"\n[阶段1] 快速估算全局平均阈值 M = {M:.2f}")

    # --- 第二遍：滑动窗口，重叠区域投票 ---
    # 初始化投票箱和用于合成增强灰度图的累加器
    votes_0 = np.zeros((h, w), dtype=np.int32)
    votes_255 = np.zeros((h, w), dtype=np.int32)

    enhanced_sum = np.zeros((h, w), dtype=np.float32)
    enhanced_count = np.zeros((h, w), dtype=np.int32)

    # 确定滑动的坐标点（确保最后边缘也能覆盖到）
    r_steps = list(range(0, h - win_h + 1, stride))
    if r_steps[-1] != h - win_h: r_steps.append(h - win_h)

    c_steps = list(range(0, w - win_w + 1, stride))
    if c_steps[-1] != w - win_w: c_steps.append(w - win_w)

    total_windows = len(r_steps) * len(c_steps)
    print(f"[阶段2] 开始滑动窗口投票... 窗口大小: {win_w}x{win_h}, 步长: {stride}, 总窗口数: {total_windows}")

    # 进度监控
    start_time = time.time()
    count = 0

    for r in r_steps:
        for c in c_steps:
            count += 1
            if count % (total_windows // 10 + 1) == 0:
                print(f"  已处理 {count}/{total_windows} 个窗口...")

            # 提取当前窗口
            block = gray_img[r:r + win_h, c:c + win_w]

            # 局部伽马变换
            mean_val = np.mean(block) / 255.0
            gamma = 1.0 + k * (mean_val - 0.5) if mean_val > 0.5 else 1.0

            block_normalized = block.astype(np.float32) / 255.0
            enhanced_block = (np.power(block_normalized, gamma) * 255).astype(np.uint8)

            # 记录增强图，用于最后平均显示
            enhanced_sum[r:r + win_h, c:c + win_w] += enhanced_block
            enhanced_count[r:r + win_h, c:c + win_w] += 1

            # 直方图与寻峰
            hist, _ = np.histogram(enhanced_block, bins=256, range=(0, 256))
            peaks = find_simple_peaks(hist)

            if len(peaks) >= 2:
                c1, c2 = min(peaks), max(peaks)
            elif len(peaks) == 1:
                c1 = c2 = peaks[0]
            else:
                c1, c2 = np.min(enhanced_block), np.max(enhanced_block)

            # 距离判定
            if c1 > M and c2 > M:
                binarized_block = np.full_like(block, 255, dtype=np.uint8)
            elif c1 < M and c2 < M:
                binarized_block = np.zeros_like(block, dtype=np.uint8)
            else:
                dist1 = np.abs(enhanced_block.astype(int) - c1)
                dist2 = np.abs(enhanced_block.astype(int) - c2)
                binarized_block = np.where(dist1 < dist2, 0, 255).astype(np.uint8)

            # 🔥 核心逻辑：不直接覆盖，而是将预测结果作为选票投给对应像素 🔥
            votes_255[r:r + win_h, c:c + win_w] += (binarized_block == 255)
            votes_0[r:r + win_h, c:c + win_w] += (binarized_block == 0)

    print(f"滑动窗口处理完毕！耗时: {time.time() - start_time:.2f} 秒")

    # --- 第三遍：统计票数，生成最终结果 ---
    # 票数多的颜色获胜
    final_binary = np.where(votes_255 > votes_0, 255, 0).astype(np.uint8)

    # 合成平滑后的增强灰度图 (避免除以0)
    safe_count = np.maximum(enhanced_count, 1)
    final_enhanced = (enhanced_sum / safe_count).astype(np.uint8)

    return final_binary, final_enhanced, votes_255, votes_0


# ================= 主程序 =================
# 建议先用一张小一点的图测试，因为步长如果设为 1 算得很慢
image_path = '1.png'

if not os.path.exists(image_path):
    print(f'错误：文件 {image_path} 不存在，请检查图片路径是否正确。')
    exit()

img = cv2.imread(image_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

gray_blurred = cv2.bilateralFilter(gray, 9, 75, 75)
print("已应用 双边滤波降噪。")

# 调用新版滑动窗口投票函数
# ⚠️ 注意：stride=1 就是你说的“一步一步走”。如果觉得太慢，可以把 stride 改成 2 或 4
binary_result, enhanced_gray, votes_255, votes_0 = sliding_window_voting_binarization(
    gray_blurred, grid_size=(10, 10), stride=2, k=5
)

# --- 生成“投票竞争热力图”展示模糊区域 ---
# 计算每个像素点票数的差异程度。差异越小（接近 50/50），说明该点越“模糊/有争议”。
total_votes = votes_255 + votes_0
total_votes[total_votes == 0] = 1  # 防止除零
uncertainty = 1.0 - (np.abs(votes_255 - votes_0) / total_votes)
uncertainty_map = (uncertainty * 255).astype(np.uint8)

# 用暖色调(红色)表示争议大(模糊)的地方，冷色调(蓝色)表示大家意见统一的地方
heatmap_img = cv2.applyColorMap(uncertainty_map, cv2.COLORMAP_JET)
heatmap_rgb = cv2.cvtColor(heatmap_img, cv2.COLOR_BGR2RGB)

# --- 显示结果 ---
# 把原来的“带框图”替换成了更有意义的“投票不确定度热力图”
plt.figure(figsize=(12, 10))
plt.subplot(221), plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)), plt.title('原始图像')
plt.subplot(222), plt.imshow(enhanced_gray, cmap='gray'), plt.title('滑动平均Gamma增强图')
plt.subplot(223), plt.imshow(binary_result, cmap='gray'), plt.title('多数投票决出结果 (纯净版)')
plt.subplot(224), plt.imshow(heatmap_rgb), plt.title('投票分歧热力图(越红说明局部越模糊)')
plt.tight_layout()
plt.show()

# 保存结果
cv2.imwrite('binary_voting_result.jpg', binary_result)
print('\n处理完成！最终二值化结果已保存。')