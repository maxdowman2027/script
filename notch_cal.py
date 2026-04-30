import math
from typing import List, Tuple
import pandas as pd
import os
import glob
import ast 
# ===================== 1. 全局配置定义（模拟C++的gSetting） =====================
class RX_TIME_CTRL:
    """输入信号定点化配置"""
    def __init__(self):
        self.syncDfeFixedBits = 12    # 输入信号总比特数
        self.syncDfeFixedClip = 0.5   # 输入信号截位值

class SINGLE_TONE_SPUR_CTRL:
    """陷波滤波器系数定点化配置"""
    def __init__(self):
        self.notchCoefFixedBitsA = 16   # Y_Coef(a系数)总比特数
        self.notchCoefFixedClipA = 4  # Y_Coef截位值
        self.notchCoefFixedBitsB = 12   # X_Coef(b系数)总比特数
        self.notchCoefFixedClipB = 4  # X_Coef截位值

class GSetting:
    """全局配置类"""
    def __init__(self):
        self.RX_TIME_CTRL = RX_TIME_CTRL()
        self.SINGLE_TONE_SPUR_CTRL = SINGLE_TONE_SPUR_CTRL()

# 全局配置实例
gSetting = GSetting()

# ===================== 2. 常量定义 =====================
SYMMETRIC = 1    # 对称量化模式
ASYMMETRIC = 0   # 非对称量化模式

# ===================== 3. 完整IIR滤波器类（整合所有功能） =====================
class IIR_FILTER_CLASS:
    def __init__(self):
        """类初始化：初始化所有成员变量"""
        # 基础状态标记
        self.initFlag = 0               # 滤波器初始化标记（0=未初始化，1=已初始化）
        self.iirNotchFixedSettingFlag = 0  # 定点化配置标记
        
        # 滤波器核心参数
        self.TapsNum = 0                # 滤波器阶数（抽头数）
        self.X_Coef = []                # 浮点分子系数（b系数，归一化后）
        self.Y_Coef = []                # 浮点分母系数（a系数，归一化后）
        self.Reg = []                   # 延迟寄存器（复数类型）
        
        # 定点化相关参数
        self.inputBits = 0              # 输入信号总比特数
        self.inputClip = 0.0            # 输入信号截位值
        self.coefBitsA = 0              # Y_Coef总比特数
        self.coefBitsClipA = 0.0        # Y_Coef截位值
        self.coefFractionBitsA = 0      # Y_Coef小数部分比特数
        self.coefBitsB = 0              # X_Coef总比特数
        self.coefBitsClipB = 0.0        # X_Coef截位值
        self.coefFractionBitsB = 0      # X_Coef小数部分比特数
        self.X_CoefFixed = []           # 定点整数分子系数
        self.Y_CoefFixed = []           # 定点整数分母系数

    # -------------------- 辅助函数：内存管理 --------------------
    def freeMemory(self):
        """释放内存（Python靠垃圾回收，仅清空列表）"""
        self.X_Coef.clear()
        self.Y_Coef.clear()
        self.Reg.clear()
        self.X_CoefFixed.clear()
        self.Y_CoefFixed.clear()
        self.TapsNum = 0
        self.initFlag = 0

    # -------------------- 辅助函数：寄存器初始化 --------------------
    def initial(self):
        """初始化延迟寄存器（置零）"""
        self.Reg = [complex(0.0, 0.0) for _ in range(self.TapsNum)]

    # -------------------- 辅助函数：浮点数转定点整数 --------------------
    def float2FixedIntOut(self, data: float, clipping: float, Bits: int, symmetryFlag: int) -> int:
        # 防止除零错误
        if clipping == 0:
            raise ValueError("clipping不能为0，会导致除零错误")
        
        # 1. 计算定点数最大值：max = 2^(Bits-1)
        max_val = 1 << (Bits - 1)
        
        # 2. 缩放：将浮点数映射到定点数范围
        temp = (data / clipping) * max_val
        
        # 3. 四舍五入取整（正数+0.5，负数-0.5）
        if temp >= 0:
            temp = int(temp + 0.5)
        else:
            temp = int(temp - 0.5)
        
        # 4. 限幅（防止定点数溢出）
        if symmetryFlag == SYMMETRIC:
            # 对称模式：[-max_val+1, max_val-1]
            if temp > max_val - 1:
                temp = max_val - 1
            elif temp < -(max_val - 1):
                temp = -(max_val - 1)
        else:
            # 非对称模式：[-max_val, max_val-1]
            if temp > max_val - 1:
                temp = max_val - 1
            elif temp < -max_val:
                temp = -max_val
        
        return int(temp)


    def iir_notch_coef(self, f0, Q, fs):

        b = [0.0] * 3
        a = [0.0] * 3
        
        if f0 != 0:

            w0 = 2.0 * math.pi * f0 / fs
            attenuate = 0.707 
            alpha = math.tan(w0 / Q / 2.0) * math.sqrt(1 - attenuate**2) / attenuate
            
            b[0] = 1.0
            b[1] = -2.0 * math.cos(w0)
            b[2] = 1.0
            
            a[0] = 1 + alpha
            a[1] = -2.0 * math.cos(w0)
            a[2] = 1 - alpha
        else:
            rou = 0.965
            b[0] = 1.0
            b[1] = -2.0
            b[2] = 1.0
            a[0] = 1.0
            a[1] = -2 * rou
            a[2] = rou * rou
        
        return b, a

    # -------------------- 核心功能2：系数归一化 --------------------
    def setCoef(self, B, A, order):

        if self.initFlag == 1:
            self.freeMemory()
        
        # 标记为已初始化
        self.initFlag = 1
        self.TapsNum = order
        
        # 拷贝系数到成员变量
        self.X_Coef = [0.0] * (self.TapsNum + 1)
        self.Y_Coef = [0.0] * (self.TapsNum + 1)
        for i in range(self.TapsNum + 1):
            self.X_Coef[i] = B[i]
            self.Y_Coef[i] = A[i]
        
        # 分母系数归一化（确保Y_Coef[0] = 1.0，增加浮点精度容错）
        if not abs(self.Y_Coef[0] - 1.0) < 1e-9:
            for i in range(self.TapsNum, -1, -1):
                self.X_Coef[i] /= self.Y_Coef[0]
                self.Y_Coef[i] /= self.Y_Coef[0]
        
        # 初始化延迟寄存器
        self.initial()
        # 重置定点化标记
        self.iirNotchFixedSettingFlag = 0

    # -------------------- 核心功能3：系数定点化 --------------------
    def setCoefFixed(self):
        """
        将归一化后的浮点系数转换为定点整数系数
        :param rxIdx: 接收通道索引（预留参数）
        """
        # 标记定点化配置开始
        self.iirNotchFixedSettingFlag = 1
        
        # 读取输入信号定点化参数（预留）
        self.inputBits = gSetting.RX_TIME_CTRL.syncDfeFixedBits
        self.inputClip = gSetting.RX_TIME_CTRL.syncDfeFixedClip
        
        # 处理Y_Coef(a系数)的定点化参数
        self.coefBitsA = gSetting.SINGLE_TONE_SPUR_CTRL.notchCoefFixedBitsA
        self.coefBitsClipA = gSetting.SINGLE_TONE_SPUR_CTRL.notchCoefFixedClipA
        int_bits_A = int(math.log10(self.coefBitsClipA) / math.log10(2.0) + 0.5)
        self.coefFractionBitsA = self.coefBitsA - int_bits_A - 1
        
        # 处理X_Coef(b系数)的定点化参数（修正所有Bug）
        self.coefBitsB = gSetting.SINGLE_TONE_SPUR_CTRL.notchCoefFixedBitsB
        self.coefBitsClipB = gSetting.SINGLE_TONE_SPUR_CTRL.notchCoefFixedClipB
        int_bits_B = int(math.log10(self.coefBitsClipB) / math.log10(2.0) + 0.5)
        self.coefFractionBitsB = self.coefBitsB - int_bits_B - 1
        
        # 初始化定点系数数组
        self.X_CoefFixed = [0] * (self.TapsNum + 1)
        self.Y_CoefFixed = [0] * (self.TapsNum + 1)
        
        # 浮点系数转定点整数
        for i in range(self.TapsNum + 1):
            self.X_CoefFixed[i] = self.float2FixedIntOut(
                self.X_Coef[i], self.coefBitsClipB, self.coefBitsB, SYMMETRIC
            )
            self.Y_CoefFixed[i] = self.float2FixedIntOut(
                self.Y_Coef[i], self.coefBitsClipA, self.coefBitsA, SYMMETRIC
            )
        return str(self.X_CoefFixed), str(self.Y_CoefFixed)

def process_single_csv(input_csv_path, output_csv_path, Q=10.0):
    # 1. 读取CSV文件
    try:
        df = pd.read_csv(input_csv_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(input_csv_path, encoding='gbk')
    except FileNotFoundError:
        print(f"❌ 错误：未找到文件 {input_csv_path}")
        return False
    except Exception as e:
        print(f"❌ 读取CSV失败 {input_csv_path}：{e}")
        return False
    # 2. 检查frequency列是否存在
    if 'frequency' not in df.columns:
        print(f"❌ 跳过 {input_csv_path}：未找到'frequency'列")
        return False
    # 3. 初始化IIR滤波器
    iir_filter = IIR_FILTER_CLASS()
    # 4. 创建空列表存储处理后的行（用于拆分多频率）
    processed_rows = []
    # 5. 遍历处理每一行
    for idx, row in df.iterrows():
        original_row = row.to_dict()  # 保留原行所有数据
        freq_val = row['frequency']
        # 情况1：no_supr → 直接保留原行，标记系数
        if isinstance(freq_val, str) and freq_val.strip().lower() == 'no_supr':
            original_row['Used_Frequency'] = 'no_supr'
            original_row['X_CoefFixed'] = 'no_supr'
            original_row['Y_CoefFixed'] = 'no_supr'
            processed_rows.append(original_row)
            continue
        
        # 情况2：解析频率值（兼容列表/单值）
        valid_freqs = []  # 存储当前行的所有有效频率
        try:
            # 步骤1：清理并解析频率值
            if isinstance(freq_val, str):
                clean_str = freq_val.strip().replace("'", '"')
                # 列表格式 → 解析为Python列表
                if '[' in clean_str and ']' in clean_str:
                    freq_list = ast.literal_eval(clean_str)
                    if not isinstance(freq_list, list):
                        raise ValueError("不是列表类型")
                    # 遍历列表提取所有有效频率
                    for item in freq_list:
                        try:
                            if isinstance(item, str):
                                item_clean = item.strip().replace(',', '.')
                                item_float = float(item_clean)
                            else:
                                item_float = float(item)
                            valid_freqs.append(item_float)
                        except (ValueError, TypeError):
                            continue  # 跳过列表中的无效项
                else:
                    # 单值字符串 → 转换为浮点数
                    clean_single = clean_str.replace(',', '.')
                    valid_freqs.append(float(clean_single))
            else:
                # 非字符串类型（int/float/列表对象）
                if isinstance(freq_val, list):
                    # 直接是列表对象 → 提取所有有效值
                    for item in freq_val:
                        try:
                            valid_freqs.append(float(item))
                        except (ValueError, TypeError):
                            continue
                else:
                    # 单值（int/float）
                    valid_freqs.append(float(freq_val))
        except (ValueError, TypeError, SyntaxError) as e:
            # 解析失败 → 保留原行，标记为invalid
            print(f"⚠️  警告：{input_csv_path} 第{idx+1}行frequency值'{freq_val}'无效 → {e}")
            original_row['Used_Frequency'] = 'invalid'
            original_row['X_CoefFixed'] = 'invalid'
            original_row['Y_CoefFixed'] = 'invalid'
            processed_rows.append(original_row)
            continue
        
        # 情况3：处理有效频率（单个/多个）
        if not valid_freqs:
            # 无有效频率 → 标记invalid
            original_row['Used_Frequency'] = 'invalid'
            original_row['X_CoefFixed'] = 'invalid'
            original_row['Y_CoefFixed'] = 'invalid'
            processed_rows.append(original_row)
        else:
            # 为每个有效频率生成一行（继承原行所有列）
            for f0 in valid_freqs:
                new_row = original_row.copy()  # 复制原行数据
                new_row['Used_Frequency'] = f0  # 记录当前使用的频率
                print(f"phy_mode is {original_row['phy_mode']}")
                if (original_row['phy_mode'] == 0) :
                    m20_pos = 0
                elif abs(f0) < 20 :
                    m20_pos = 1 
                elif abs(f0) < 40 :
                    m20_pos = 3
                elif abs(f0) < 60 :
                    m20_pos = 5
                else:
                    m20_pos = 7
                
                if f0 < 0 :
                    m20_pos = m20_pos * (-1)

                notch_freq = float(abs((m20_pos * 10) - f0))
                if abs(notch_freq) > 7 :
                    fs = 40.0
                else :
                    fs = 20.0
                print(f"f0 :{f0} ,m20_pos:{m20_pos} ,notch_freq:{notch_freq}")
                # 计算该频率的系数
                B, A = iir_filter.iir_notch_coef(notch_freq, Q, fs)
                order = 2
                iir_filter.setCoef(B, A,order)
                x_fixed, y_fixed = iir_filter.setCoefFixed()
                # 填入系数
                new_row['X_CoefFixed'] = x_fixed
                new_row['Y_CoefFixed'] = y_fixed
                processed_rows.append(new_row)
    # 6. 将处理后的行转为DataFrame
    processed_df = pd.DataFrame(processed_rows)
    # 调整列顺序（把新增列放在frequency后，便于查看）
    cols = df.columns.tolist()
    if 'Used_Frequency' not in cols:
        cols.insert(cols.index('frequency')+1, 'Used_Frequency')
    if 'X_CoefFixed' not in cols:
        cols.insert(cols.index('Used_Frequency')+1, 'X_CoefFixed')
    if 'Y_CoefFixed' not in cols:
        cols.insert(cols.index('X_CoefFixed')+1, 'Y_CoefFixed')
    processed_df = processed_df[cols]
    # 7. 保存文件（兼容不同编码）
    try:
        processed_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    except Exception:
        processed_df.to_csv(output_csv_path, index=False, encoding='gbk')
    return True

def batch_process_csv(input_dir, output_dir, Q=10.0, recursive=False):

    if not os.path.exists(input_dir):
        print(f"❌ 错误：输入目录 {input_dir} 不存在")
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 输出目录已准备：{output_dir}")

    search_pattern = os.path.join(input_dir, "**/*.csv") if recursive else os.path.join(input_dir, "*.csv")
    csv_files = glob.glob(search_pattern, recursive=recursive)

    if not csv_files:
        print(f"⚠️  警告：在 {input_dir} 下未找到任何CSV文件")
        return

    processed_count = 0
    for csv_path in csv_files:
        file_name = os.path.basename(csv_path)
        file_base, file_ext = os.path.splitext(file_name)
        new_file_name = f"{file_base}_coef{file_ext}"
        output_csv_path = os.path.join(output_dir, new_file_name)

        # 处理单个文件
        print(f"\n🔄 正在处理：{csv_path}")
        if process_single_csv(csv_path, output_csv_path,Q):
            print(f"✅ 处理完成：{output_csv_path}")
            processed_count += 1
        else:
            print(f"❌ 处理失败：{csv_path}")

    print(f"\n📊 批量处理完成！总计找到{len(csv_files)}个CSV文件，成功处理{processed_count}个")
    print(f"📁 所有输出文件已保存至：{output_dir}")


    # if __name__ == "__main__":
    #     iir_filter = IIR_FILTER_CLASS()

    #     f0 = 1.0    
    #     Q = 5.0    
    #     fs = 40.0  
    #     B, A = iir_filter.iir_notch_coef(f0, Q, fs)
    #     print("=== 1.iir_notch_coef ===")
    #     print(f"B = {[round(x, 6) for x in B]}")
    #     print(f"A = {[round(x, 6) for x in A]}")


    #     order = 2  
    #     iir_filter.setCoef(B, A, order)
    #     print("\n=== 2.setCoef ===")
    #     print(f"X_Coef = {[round(x, 6) for x in iir_filter.X_Coef]}")
    #     print(f"Y_Coef = {[round(x, 6) for x in iir_filter.Y_Coef]}")



    #     iir_filter.setCoefFixed(rxIdx=0)
    #     print("\n=== 3.setCoefFixed ===")
    #     print(f"X_CoefFixed = {iir_filter.X_CoefFixed}")
    #     print(f"Y_CoefFixed = {iir_filter.Y_CoefFixed}")


if __name__ == "__main__":
    INPUT_DIR = r"D:\users\gxu\spur_scan\scan_data\2G\result"       # 输入目录（Windows路径，r前缀避免转义）
    OUTPUT_DIR = r"D:\users\gxu\spur_scan\scan_data\2G\result"     # 输出目录
    QUALITY_FACTOR = 5.0             # 陷波滤波器Q值
    RECURSIVE_SEARCH = False          # 是否递归搜索子目录（True=是，False=仅当前目录）

    # ---------- 执行批量处理 ----------
    batch_process_csv(
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
        Q=QUALITY_FACTOR,
        recursive=RECURSIVE_SEARCH
    )
