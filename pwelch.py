import numpy as np
from scipy.signal import get_window 
import matplotlib.pyplot as plt

def my_pwelch(
    x, 
    fs=1.0, 
    nperseg=None, 
    noverlap=None, 
    window='hann', 
    return_onesided=True,
    scaling='spectrum'
):
    """
    纯Python实现韦尔奇法功率谱密度（PSD）估计，对齐scipy.signal.pwelch接口
    :param x: 输入信号（1维numpy数组）
    :param fs: 采样频率（Hz），默认1.0
    :param nperseg: 每个分段的长度，默认min(256, len(x))
    :param noverlap: 分段重叠长度，默认nperseg//2（50%重叠）
    :param window: 窗函数类型，默认'hann'（汉宁窗），支持'hamming'/'blackman'等
    :param return_onesided: 是否返回单边谱（工程常用），默认True
    :param scaling: 缩放方式，'density'（PSD，V²/Hz）或'spectrum'（功率谱，V²），默认'density'
    :return: (f, Pxx) - 频率轴、功率谱密度/功率谱
    """
    # -------------------------- 步骤1：参数校验与初始化 --------------------------
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("输入信号必须是1维数组！")
    n_total = len(x)
    
    # 默认分段长度（和scipy一致）
    if nperseg is None:
        nperseg = min(256, n_total)
    if nperseg > n_total:
        raise ValueError(f"分段长度nperseg={nperseg}不能大于信号长度{n_total}！")
    
    # 默认重叠长度（50%重叠）
    if noverlap is None:
        noverlap = nperseg // 2
    if noverlap >= nperseg:
        raise ValueError(f"重叠长度noverlap={noverlap}不能≥分段长度nperseg={nperseg}！")
    
    # 分段步长（相邻分段的起始间隔）
    step = nperseg - noverlap
    # 计算有效分段数（避免最后一段长度不足）
    n_segments = 1 + (n_total - nperseg) // step
    if n_segments < 1:
        raise ValueError(f"信号长度{n_total}不足，无法按nperseg={nperseg}分段！")

    # -------------------------- 步骤2：生成窗函数（能量归一） --------------------------
    # 获取窗函数（长度=分段长度）
    win = get_window(window, nperseg)
    # 窗能量归一（保证功率谱幅值正确）
    win_norm = win / np.sum(win ** 2)

    # -------------------------- 步骤3：分段处理 + 周期图计算 --------------------------
    # 存储所有分段的周期图
    periodograms = []
    for i in range(n_segments):
        # 提取当前分段的信号
        start = i * step
        end = start + nperseg
        x_seg = x[start:end]
        
        # 加窗处理
        x_win = x_seg * win_norm
        
        # FFT计算（快速傅里叶变换）
        fft_vals = np.fft.fft(x_win, n=nperseg)
        
        # 计算周期图（核心公式）
        # 周期图 = |FFT|² / (fs * 窗能量) → 因窗已归一，简化为|FFT|² / fs
        periodogram = np.abs(fft_vals) ** 2 / fs
        
        # 缩放方式：density（PSD，V²/Hz）或 spectrum（功率谱，V²）
        if scaling == 'spectrum':
            periodogram *= fs / nperseg  # 功率谱：积分PSD得到总功率
        
        periodograms.append(periodogram)

    # -------------------------- 步骤4：周期图平均（降低方差） --------------------------
    Pxx = np.mean(periodograms, axis=0)

    # -------------------------- 步骤5：生成频率轴 + 单边谱处理 --------------------------
    # 生成原始频率轴（0 ~ fs，双边）
    f = np.fft.fftfreq(nperseg, 1/fs)
    
    # 处理单边谱（工程常用，仅保留0~fs/2）
    if return_onesided:
        # 筛选正频率索引
        idx = f >= 0
        f = f[idx]
        Pxx = Pxx[idx]
        
        # 单边谱幅值修正（除直流和Nyquist频率外，其余×2，保证功率守恒）
        if len(f) > 1:
            Pxx[1:-1] *= 2

    return f, Pxx

# -------------------------- 验证：对比scipy.signal.pwelch --------------------------
if __name__ == "__main__":
    # 1. 生成测试信号（50Hz正弦波+高斯噪声，便于验证）
    fs = 1000  # 采样频率1000Hz
    t = np.linspace(0, 1, fs, endpoint=False)  # 1秒时间轴
    f0 = 50    # 信号主频50Hz
    x = np.sin(2 * np.pi * f0 * t) + 0.5 * np.random.randn(len(t))  # 信号+噪声

    # 2. 调用自定义my_pwelch
    f_my, Pxx_my = my_pwelch(
        x=x,
        fs=fs,
        nperseg=256,
        noverlap=128,
        window='hann',
        return_onesided=True,
        scaling='density'
    )

    # 3. 调用scipy.pwelch（基准对比）
    from scipy.signal import pwelch
    f_scipy, Pxx_scipy = pwelch(
        x=x,
        fs=fs,
        nperseg=256,
        noverlap=128,
        window='hann',
        return_onesided=True,
        scaling='density'
    )

    # 4. 打印关键对比结果
    print("=== 频率轴对比（前5个点）===")
    print(f"自定义实现：{f_my[:5]}")
    print(f"scipy实现：{f_scipy[:5]}")

    print("\n=== 功率谱峰值对比 ===")
    peak_idx_my = np.argmax(Pxx_my)
    peak_idx_scipy = np.argmax(Pxx_scipy)
    print(f"自定义实现 - 峰值频率：{f_my[peak_idx_my]:.2f}Hz，PSD值：{Pxx_my[peak_idx_my]:.4f}")
    print(f"scipy实现 - 峰值频率：{f_scipy[peak_idx_scipy]:.2f}Hz，PSD值：{Pxx_scipy[peak_idx_scipy]:.4f}")

    # 5. 画图对比（转dB显示，更直观）
    plt.figure(figsize=(12, 6))

    # 自定义实现的PSD
    plt.subplot(1, 2, 1)
    plt.plot(f_my, 10 * np.log10(Pxx_my), color='blue', label='my_pwelch')
    plt.title('自定义pwelch - PSD (dB/Hz)')
    plt.xlabel('频率 (Hz)')
    plt.ylabel('功率谱密度 (dB/Hz)')
    plt.xlim(0, 100)  # 聚焦0~100Hz（50Hz主频）
    plt.grid(True, alpha=0.3)
    plt.legend()

    # scipy实现的PSD
    plt.subplot(1, 2, 2)
    plt.plot(f_scipy, 10 * np.log10(Pxx_scipy), color='red', label='scipy.pwelch')
    plt.title('scipy.pwelch - PSD (dB/Hz)')
    plt.xlabel('频率 (Hz)')
    plt.ylabel('功率谱密度 (dB/Hz)')
    plt.xlim(0, 100)
    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.tight_layout()
    plt.show()