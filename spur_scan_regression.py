import os
import re
import glob
import ast
import pandas as pd
import numpy as np

# ===================== 核心配置 =====================
# 固定返回的列名（与CSV列名完全一致）
TARGET_COLUMNS = ['diff_pwr', 'phy_mode','channel','frequency','Used_Frequency', 'X_CoefFixed', 'Y_CoefFixed']

def extract_number_list(input_content):
    """
    提取字符串格式的数字列表（如"[1235,1552,15]"）为正常的整数列表
    :param input_content: 输入内容（支持带空格/换行/制表符的字符串，如"[1235, 1552, 15]"）
    :return: 解析后的整数列表；解析失败返回空列表，并打印错误提示
    """
    # 步骤1：统一转换为字符串，处理非字符串输入（如误传列表/数字）
    if not isinstance(input_content, str):
        # 若输入本身是列表，直接返回（兼容边界情况）
        if isinstance(input_content, list):
            # 过滤列表中的非整数元素，仅保留数字
            return [int(x) for x in input_content if isinstance(x, (int, float)) and x.is_integer()]
        print(f"❌ 输入类型错误，需传入字符串（当前类型：{type(input_content)}）")
        return []
    
    # 步骤2：清洗字符串（去除所有空白字符：空格、换行、制表符等）
    cleaned_str = input_content.strip()  # 去除首尾空白
    cleaned_str = cleaned_str.replace(" ", "").replace("\n", "").replace("\t", "")
    
    # 步骤3：校验并去除首尾的[]符号
    if not (cleaned_str.startswith("[") and cleaned_str.endswith("]")):
        print(f"❌ 输入格式错误，未以[]包裹（当前内容：{input_content}）")
        return []
    # 去掉首尾的[]，得到纯数字逗号分隔的字符串
    num_str = cleaned_str[1:-1]
    
    # 步骤4：处理空列表情况（如"[]"）
    if num_str == "":
        return []
    
    # 步骤5：分割并转换为整数
    result = []
    # 按逗号分割成单个数字字符串
    num_str_list = num_str.split(",")
    for idx, s in enumerate(num_str_list):
        # 跳过空元素（如"[123,,456]"中的空值）
        if s.strip() == "":
            print(f"⚠️  第{idx+1}个元素为空，已跳过")
            continue
        try:
            # 转换为整数（兼容浮点型数字如"123.0"）
            num = float(s)
            if not num.is_integer():
                print(f"⚠️  第{idx+1}个元素{s}不是整数，已跳过")
                continue
            result.append(int(num))
        except ValueError:
            print(f"❌ 第{idx+1}个元素{s}无法转换为整数，已跳过")
    
    return result



def parse_column_value(raw_value) -> list:
    """
    通用解析函数：返回原生Python列表（保留单行列的原始完整数据）
    """
    if pd.isna(raw_value) or raw_value is None or raw_value == '':
        return []
    if isinstance(raw_value, str):
        clean_str = raw_value.strip()
        if clean_str.startswith('[') and clean_str.endswith(']'):
            try:
                parsed_list = ast.literal_eval(clean_str)
                return parsed_list if isinstance(parsed_list, list) else [parsed_list]
            except (SyntaxError, ValueError):
                return [clean_str.strip('[]').strip("'\"")]
        else:
            return [clean_str.strip("'\"")]
    elif isinstance(raw_value, list):
        return raw_value
    else:
        return [raw_value]

def get_multi_row_data_generator(file_path) -> dict:
    """
    生成器：读取N行并保留这N行的所有列完整数据
    返回格式（以N=3行为例）：
    {
        # 每列是二维列表：外层=行索引（0/1/2），内层=该行该列的原始完整数据
        'diff_pwr': [[1.2,3.5], [1.3,3.6], [1.4,3.7]],    # 3行的diff_pwr原始数据
        'phy_mode': [['802.11b'], ['802.11b'], ['802.11g']], # 3行的phy_mode原始数据
        'channel': [[2], [3], [4]],                        # 3行的channel原始数据
        'frequency': [[50,60,70], [51,61,71], [52,62,72]], # 3行的frequency原始数据
        'Used_Frequency': [[50,60], [51,61], [52,62]],     # 3行的Used_Frequency原始数据
        'X_CoefFixed': [[0.1,0.2], [0.11,0.21], [0.12,0.22]], # 3行的X_CoefFixed原始数据
        'Y_CoefFixed': [[0.4,0.5], [0.41,0.51], [0.42,0.52]], # 3行的Y_CoefFixed原始数据
        # 辅助信息
        'read_rows': 3,                # 本次读取的总行数
        'original_start_row': 2,       # 本次读取的起始行号（原文件）
        'original_end_row': 4,         # 本次读取的结束行号（原文件）
        'skip_rows': 3,                # 跳行步数（=read_rows）
        'next_process_row': 5          # 下一次读取的起始行号
    }
    """
    # 读取CSV文件（兼容编码）
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='gbk')
    
    # 验证列存在性
    missing_cols = [col for col in TARGET_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"文件{file_path}缺失指定列：{', '.join(missing_cols)}")

    total_rows = len(df)
    current_idx = 0  # 当前处理的起始索引（从0开始）

    while current_idx < total_rows:
        # ========== 1. 确定本次要读取的行数（基于起始行的frequency长度） ==========
        start_row = df.iloc[current_idx]
        start_row_num = current_idx + 1  # 起始行号（原文件，从1开始）
        frequency_list = parse_column_value(start_row['frequency'])

        # 过滤无效行（frequency=['no_spur'] → 仅跳过当前行）
        if frequency_list == ['no_spur']:
            print(f"⚠️  跳过原行{start_row_num}：frequency=['no_spur']")
            current_idx += 1
            continue

        # 验证frequency有效性 → 确定本次读取行数
        if not isinstance(frequency_list, list) or len(frequency_list) == 0:
            print(f"⚠️  跳过原行{start_row_num}：frequency非有效列表（值={start_row['frequency']}）")
            current_idx += 1
            continue
        
        read_rows = len(frequency_list)  # 本次要读取的总行数
        # 边界处理：剩余行数不足时，读取剩余所有行
        actual_read_rows = min(read_rows, total_rows - current_idx)
        end_idx = current_idx + actual_read_rows  # 结束索引（不包含）
        end_row_num = current_idx + actual_read_rows  # 结束行号（原文件）

        print(f"\n📌 读取原行{start_row_num}~{end_row_num}：共{actual_read_rows}行（计划{read_rows}行，剩余行数限制）")

        # ========== 2. 初始化：收集N行的所有列数据 ==========
        multi_row_data = {col: [] for col in TARGET_COLUMNS}
        # 辅助信息
        multi_row_data['read_rows'] = actual_read_rows
        multi_row_data['original_start_row'] = start_row_num
        multi_row_data['original_end_row'] = end_row_num
        multi_row_data['skip_rows'] = read_rows  # 跳行步数=计划读取行数
        multi_row_data['next_process_row'] = end_row_num + 1

        # ========== 3. 逐行读取并保留每一行的原始完整数据 ==========
        for row_idx in range(current_idx, end_idx):
            current_row = df.iloc[row_idx]
            current_row_num = row_idx + 1  # 当前行号（原文件）

            # 解析当前行的所有列 → 保留原始完整数据
            for col in TARGET_COLUMNS:
                parsed_full_list = parse_column_value(current_row[col])
                multi_row_data[col].append(parsed_full_list)  # 追加当前行的原始数据

            print(f"   ✅ 已保留原行{current_row_num}数据：{col}={parsed_full_list}（长度={len(parsed_full_list)}）")

        # ========== 4. 打印验证：确保多行数据都被保留 ==========
        print(f"\n   📝 本次读取{actual_read_rows}行的所有列数据（无丢失）：")
        for col in TARGET_COLUMNS:
            row_count = len(multi_row_data[col])
            total_elem = sum([len(row_data) for row_data in multi_row_data[col]])
            print(f"      - {col}：共{row_count}行，累计元素数={total_elem} → 示例={multi_row_data[col][:2]}")

        # ========== 5. 返回多行完整数据 ==========
        yield multi_row_data

        # ========== 6. 跳行处理（跳过计划读取的行数） ==========
        current_idx += read_rows  # 跳行=计划读取行数（即使实际读取行数更少）
        print(f"   ✅ 本次{actual_read_rows}行数据保留完成，跳行{read_rows}步 → 下一次读取原行{current_idx+1 if current_idx < total_rows else '结束'}")

def external_usage_example(multi_row_data):
    """
    外部使用示例：使用读取的N行完整数据（不丢任何行/列值）
    """
    print("\n" + "="*80)
    print("📝 外部使用示例（保留N行完整数据，不丢任何值）")
    print("="*80)

    # ========== 1. 基础信息 ==========
    read_rows = multi_row_data['read_rows']
    start_row = multi_row_data['original_start_row']
    end_row = multi_row_data['original_end_row']
    print(f"\n1. 读取基础信息：")
    print(f"   - 读取行数：{read_rows}行（原文件{start_row}~{end_row}行）")
    print(f"   - 下一次读取行：{multi_row_data['next_process_row']}")

    # ========== 2. 访问指定行的指定列数据（核心需求） ==========
    print(f"\n2. 访问指定行的列数据：")
    # 示例：访问第0行（原文件start_row）的X_CoefFixed
    row_0_X = multi_row_data['X_CoefFixed'][0]
    print(f"   - 第1行（原{start_row}行）X_CoefFixed：{row_0_X}")
    
    # 示例：访问第1行（原文件start_row+1）的Y_CoefFixed
    if read_rows >= 2:
        row_1_Y = multi_row_data['Y_CoefFixed'][1]
        print(f"   - 第2行（原{start_row+1}行）Y_CoefFixed：{row_1_Y}")

    # ========== 3. 遍历所有行的所有列数据 ==========
    print(f"\n3. 遍历{read_rows}行的所有X_CoefFixed数据：")
    for row_idx in range(read_rows):
        if row_idx >= len(multi_row_data['X_CoefFixed']):
            break  # 处理实际读取行数不足的情况
        row_num = start_row + row_idx
        x_data = multi_row_data['X_CoefFixed'][row_idx]
        print(f"   - 原行{row_num} X_CoefFixed：{x_data} → 元素数={len(x_data)}")

    # ========== 4. 整合多行同列数据（示例） ==========
    print(f"\n4. 整合多行同列数据：")
    # 整合所有行的X_CoefFixed到一个列表
    all_X = []
    for row_x in multi_row_data['X_CoefFixed']:
        all_X.extend(row_x)  # 保留所有元素，不丢失
    print(f"   - 所有行X_CoefFixed整合：{all_X} → 总元素数={len(all_X)}")

    # 计算所有行Y_CoefFixed的数值总和
    all_Y_numeric = []
    for row_y in multi_row_data['Y_CoefFixed']:
        all_Y_numeric.extend([y for y in row_y if isinstance(y, (int, float))])
    Y_total = sum(all_Y_numeric)
    print(f"   - 所有行Y_CoefFixed数值总和：{Y_total} → 平均值={np.mean(all_Y_numeric):.4f}")

    print("\n" + "="*80)
    print("✅ 多行数据使用完成，无任何行/列值丢失")
    print("="*80)

    # inst.WIFI_RX_range(chan_in=[9], data_rate = ['mcs0_vht'], rx_range=['-100,-20'], cable_lose = 9.8, bw = 0, ldpc_flag = 0,mrc_flag = 0, stbc_flag=0, phymd=0, 
    #                    m20_position=0, nss2_flag=0,chan_sel = 0, name_str='bw20_11ac_2G_lna4',mimo_siso_mode='siso',chip_version='rls3.0',iqv_no=1, packnum=100, pwr_step=1, plot_en=1, sync_print=1, is_asic=1)
    if multi_row_data['channel'][0][0] < 15 :
        cable_lose = 4.3
    else :
        cable_lose = 6.8
    print(f"----------------------------------读取行数:{read_rows}--------------------------------------------------")
    print(f"---------------------------------------------diff_pwr:{multi_row_data['diff_pwr']}------------------------")
    max_diff_pwr_value = max(multi_row_data['diff_pwr'][0])
    max_diff_pwr_index = multi_row_data['diff_pwr'][0].index(max_diff_pwr_value)
    print(f"------------------------------------max_diff_pwr_value:{max_diff_pwr_value},max_diff_pwr_index:{max_diff_pwr_index} ---------------------------------") 
    max_spur_frequency  = multi_row_data['Used_Frequency'][max_diff_pwr_index]
    print(f"-------------------------------Used_Frequency:{multi_row_data['Used_Frequency']} ,max_spur_frequency:{max_spur_frequency}----------------------")
    max_spur_x_coef = multi_row_data['X_CoefFixed'][max_diff_pwr_index]
    max_spur_y_coef = multi_row_data['Y_CoefFixed'][max_diff_pwr_index]
    print(f"------------------------------all_X:{all_X[1]},max_spur_x_coef:{max_spur_x_coef},max_spur_y_coef:{max_spur_y_coef}---------------------------------------------------")
    print(f"------------------------------------{multi_row_data['channel'][0][0]}-----------------------------------")
    name_str = 'bw' + str(multi_row_data['phy_mode'][0][0]) +'_' 'vht' + 'channel_' + str(multi_row_data['channel'][0][0])
    print(f"-------------------------------------{name_str}-----------------------------------------")
    # print(f"inst.WIFI_RX_range(chan_in={multi_row_data['channel'][0][0]}, data_rate = ['mcs0_vht'], rx_range=['-100,-20'], cable_lose = {cable_lose}, bw = {multi_row_data['phy_mode'][0][0]}, ldpc_flag = 1,mrc_flag = 0, stbc_flag=0, phymd={multi_row_data['phy_mode'][0][0]}, m20_position=0, nss2_flag=0,chan_sel = 0, name_str={name_str}  ,mimo_siso_mode='siso',chip_version='rls3.0',iqv_no=1, packnum=100, pwr_step=1, plot_en=1, sync_print=1, is_asic=1)")
    rls3p0_newfeature_notch_test(max_spur_frequency=max_spur_frequency[0],spur_frequency=multi_row_data['Used_Frequency'],x_coef=max_spur_x_coef,y_coef=max_spur_y_coef,spur_num=read_rows,diff_pwr=multi_row_data['diff_pwr'], chan_in=multi_row_data['channel'][0][0] ,phy_mode=multi_row_data['phy_mode'][0][0] )



def rls3p0_newfeature_notch_test(max_spur_frequency,spur_frequency,x_coef,y_coef,spur_num,diff_pwr, chan_in ,phy_mode ):
    if chan_in < 15 :
        cable_lose = 4.3
        wifi_format = 'vht'
    else :
        cable_lose = 6.8
        wifi_format = 'hesu'
    print(f"max_spur_frequency is {max_spur_frequency} ,type: {type(max_spur_frequency)}")
    max_spur_frequency = int(max_spur_frequency)

    if abs(max_spur_frequency) <= 20 :
        m20_pos = 0 
    elif abs(max_spur_frequency) <= 40 :
        m20_pos = 1
    elif abs(max_spur_frequency) <= 60 :
        m20_pos = 3
    else:
        m20_pos = 5
    
    if max_spur_frequency < 0 :
        m20_pos = m20_pos * (-1)
    # print(f"phy_mode:{phy_mode},{type(phy_mode)} ,chan_in:{chan_in}, {type(chan_in)}")
    diff_pwr = diff_pwr[0]
    print(f"spur_frequency:{spur_frequency} ,len:{len(spur_frequency)} ,x_coef:{x_coef[0]} ,spur_num:{spur_num},diff_pwr:{diff_pwr}")
    print(f"spur_frequency:{type(spur_frequency[0])}  ,x_coef:{type(x_coef[0])} ,spur_num:{type(spur_num)},diff_pwr:{type(diff_pwr[0])} ")
    name_str = 'bw' + str(phy_mode) +'_' + wifi_format + 'channel_' + str(chan_in)

    # for i in [0,1] :
    #     if i == 1 : #notch enable 
    #         self.HWREG.PHY_FFT.FFT_SPUR_CONF.reg_spur_cancel_ena = 1
    #         if max_spur_frequency > 7 or max_spur_frequency < -7 :
    #             self.HWREG.PHY_RXTIME.DFE_CONF0.reg_notch_work_at_40m = 1
    #         else:
    #             self.HWREG.PHY_RXTIME.DFE_CONF0.reg_notch_work_at_40m = 0

    #         self.HWREG.PHY_RXTIME.DFE_CONF_PUNC.reg_single_tone_notch_en_max_vga_code_th=0

    #         self.HWREG.PHY_RXTIME.DFE_NOTCH_X01_0CH.reg_notch_x0c_0ch = x_coef[0] 
    #         self.HWREG.PHY_RXTIME.DFE_NOTCH_X01_0CH.reg_notch_x1c_0ch = x_coef[1]
    #         self.HWREG.PHY_RXTIME.DFE_NOTCH_X2_0CH.reg_sync_notch_en = 1
    #         self.HWREG.PHY_RXTIME.DFE_NOTCH_X2_0CH.reg_notch_x2c_0ch = x_coef[2]
    #         self.HWREG.PHY_RXTIME.DFE_NOTCH_Y_0CH.reg_notch_y0c_0ch = y_coef[0]
    #         self.HWREG.PHY_RXTIME.DFE_NOTCH_Y_0CH.reg_notch_y1c_0ch = y_coef[1]
    #         # self.mem.wrm(0x600a9e24, 13, 0, 192)  # 3M * 64

    #         self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ0.reg_ant0_spur_cancel_num = spur_num  # * 64
    #         if spur_num == 1:
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ0.reg_ant0_single_tone_freq_mhz0 = spur_frequency[0]*64  # * 64
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_PWR0.reg_ant0_single_tone_pwr0 = diff_pwr[0] - 110
    #         elif spur_num == 2:
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ0.reg_ant0_single_tone_freq_mhz0 = spur_frequency[0]*64  # * 64
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ0.reg_ant0_single_tone_freq_mhz1 = spur_frequency[1]*64  # * 64
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_PWR0.reg_ant0_single_tone_pwr0 = diff_pwr[0] - 110
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_PWR0.reg_ant0_single_tone_pwr1 = diff_pwr[1] - 110
    #         elif spur_num == 3: 
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ0.reg_ant0_single_tone_freq_mhz0 = spur_frequency[0]*64  # * 64
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ0.reg_ant0_single_tone_freq_mhz1 = spur_frequency[1]*64  # * 64
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ1.reg_ant0_single_tone_freq_mhz2 = spur_frequency[2]*64  # * 64
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_PWR0.reg_ant0_single_tone_pwr0 = diff_pwr[0] - 110
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_PWR0.reg_ant0_single_tone_pwr1 = diff_pwr[1] - 110
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_PWR0.reg_ant0_single_tone_pwr2 = diff_pwr[2] - 110
    #         elif spur_num == 4 :
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ0.reg_ant0_single_tone_freq_mhz0 = spur_frequency[0]*64  # * 64
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ0.reg_ant0_single_tone_freq_mhz1 = spur_frequency[1]*64  # * 64
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ1.reg_ant0_single_tone_freq_mhz2 = spur_frequency[2]*64  # * 64                
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_FREQ1.reg_ant0_single_tone_freq_mhz3 = spur_frequency[3]*64  # * 64    
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_PWR0.reg_ant0_single_tone_pwr0 = diff_pwr[0] - 110
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_PWR0.reg_ant0_single_tone_pwr1 = diff_pwr[1] - 110
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_PWR0.reg_ant0_single_tone_pwr2 = diff_pwr[2] - 110            
    #             self.HWREG.PHY_FFT.FFT_SPUR_TONE_PWR0.reg_ant0_single_tone_pwr3 = diff_pwr[3] - 110            
    #     else :
    #         self.HWREG.PHY_FFT.FFT_SPUR_CONF.reg_spur_cancel_ena = 0
    #         self.HWREG.PHY_RXTIME.DFE_NOTCH_X2_0CH.reg_sync_notch_en = 0
    #     if wifi_format == 'vht':
    #         print(f"inst.WIFI_RX_range(chan_in={chan_in}, data_rate = ['mcs0_vht','mcs1_vht','mcs2_vht','mcs3_vht','mcs4_vht','mcs5_vht','mcs6_vht','mcs7_vht','mcs8_vht'], rx_range=['-100,-20'], cable_lose = {cable_lose}, bw = {phy_mode}, ldpc_flag = 1,mrc_flag = 0, stbc_flag=0, phymd={phy_mode}, m20_position={m20_pos}, nss2_flag=0,chan_sel = 0, name_str={name_str},mimo_siso_mode='siso',chip_version='rls3.0',iqv_no=1, packnum=100, pwr_step=1, plot_en=1, sync_print=1, is_asic=1)")
    #         # inst.WIFI_RX_range(chan_in=chan_in, data_rate = ['mcs0_vht','mcs1_vht','mcs2_vht','mcs3_vht','mcs4_vht','mcs5_vht','mcs6_vht','mcs7_vht','mcs8_vht'], rx_range=['-100,-20'], cable_lose = cable_lose, bw = phy_mode, ldpc_flag = 1,mrc_flag = 0, stbc_flag=0, phymd=phy_mode, m20_position=m20_pos, nss2_flag=0,chan_sel = 0, name_str={name_str}  ,
    #         #     mimo_siso_mode='siso',chip_version='rls3.0',iqv_no=1, packnum=100, pwr_step=1, plot_en=1, sync_print=1, is_asic=1)
    #     else : 
    #         print(f"inst.WIFI_RX_hesu(chan_in={chan_in}, mcs=[0,1,2,3,4,5,6,7,8,9], giltf = [1], maxpwr = -50, minpwr = -100, cable_lose = {cable_lose} , bw = {phy_mode}, ldpc_flag = 1, mrc_flag = 0, stbc=0, phymd={phy_mode}, m20_position={m20_pos}, nss2_flag=0, chan_sel = 0, pe=0, mimo_siso_mode='siso', tag_str='',chip_version='rls3.0',precise_mode=0, date=0, iqv_no=1, pwr_adaption=0, packnum=100, len=4096, sync_print=1, is_asic=1)")
    #         # inst.WIFI_RX_hesu(chan_in=chan_in, mcs=[0,1,2,3,4,5,6,7,8,9], giltf = [1], maxpwr = -50, minpwr = -100, cable_lose = cable_lose , bw = phy_mode, ldpc_flag = 1, mrc_flag = 0, stbc=0, phymd=phy_mode, m20_position=m20_pos, nss2_flag=0, chan_sel = 0, pe=0, mimo_siso_mode='siso', tag_str='',chip_version='rls3.0',precise_mode=0, date=0, iqv_no=1, pwr_adaption=0, packnum=100, len=4096, sync_print=1, is_asic=1)
 



            


def process_single_file(file_path):
    """
    处理单个文件：保留多行完整数据
    """
    process_result = {
        "file_path": file_path,
        "total_original_rows": 0,
        "total_read_groups": 0,  # 读取的批次组数
        "total_read_rows": 0,    # 累计读取的行数
        "success": True,
        "error": None
    }

    # try:
    df = pd.read_csv(file_path, encoding='utf-8') if os.path.exists(file_path) else pd.DataFrame()
    process_result["total_original_rows"] = len(df)
    # 获取多行数据生成器
    data_gen = get_multi_row_data_generator(file_path)
    # 遍历每个读取批次
    for multi_row_data in data_gen:
        process_result["total_read_groups"] += 1
        process_result["total_read_rows"] += multi_row_data['read_rows']
        # 外部使用示例
        external_usage_example(multi_row_data)

    # except Exception as e:
    #     process_result["success"] = False
    #     process_result["error"] = str(e)
    #     print(f"❌ 处理文件{file_path}失败：{str(e)}")

    return process_result

def batch_process(input_dir, recursive=False):
    """
    批量处理目录下的所有文件
    """
    # 筛选文件
    search_pattern = os.path.join(input_dir, "**/*.csv") if recursive else os.path.join(input_dir, "*.csv")
    csv_files = glob.glob(search_pattern, recursive=recursive)
    pattern = re.compile(r'spur_scan_result_(\d+)G_coef\.csv', re.IGNORECASE)
    target_files = [f for f in csv_files if pattern.match(os.path.basename(f))]

    if not target_files:
        print(f"⚠️  目录{input_dir}下未找到符合格式的文件（spur_scan_result_*G_coef.csv）")
        return

    # 批量统计
    batch_stats = {
        "total_files": len(target_files),
        "success_files": 0,
        "fail_files": 0,
        "total_read_groups": 0,
        "total_read_rows": 0
    }

    # 处理每个文件
    for file_path in target_files:
        print(f"\n" + "-"*100)
        print(f"🔄 开始处理文件：{file_path}")
        print("-"*100)
        
        file_result = process_single_file(file_path)
        if file_result["success"]:
            batch_stats["success_files"] += 1
            batch_stats["total_read_groups"] += file_result["total_read_groups"]
            batch_stats["total_read_rows"] += file_result["total_read_rows"]
            print(f"\n📊 {file_path} 处理统计：")
            print(f"   - 原文件总行数：{file_result['total_original_rows']}")
            print(f"   - 读取批次组数：{file_result['total_read_groups']}")
            print(f"   - 累计读取行数：{file_result['total_read_rows']}")
        else:
            batch_stats["fail_files"] += 1

    # 全局汇总
    print(f"\n" + "="*100)
    print(f"📊 全局批量处理汇总")
    print("="*100)
    print(f"   - 总文件数：{batch_stats['total_files']}")
    print(f"   - 成功处理：{batch_stats['success_files']}")
    print(f"   - 处理失败：{batch_stats['fail_files']}")
    print(f"   - 累计读取批次：{batch_stats['total_read_groups']}")
    print(f"   - 累计读取行数：{batch_stats['total_read_rows']}")

# ===================== 运行入口 =====================
if __name__ == "__main__":
    # 替换为你的CSV文件所在目录
    INPUT_DIR = r"D:\users\gxu\spur_scan\260206\scprit_test"
    # 是否递归处理子目录
    RECURSIVE_SEARCH = False

    # 执行批量处理
    batch_process(input_dir=INPUT_DIR, recursive=RECURSIVE_SEARCH)
