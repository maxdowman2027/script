import math

def calculate_wifi_payload_length(protocol, bw_mhz, n_sym, mcs, n_ss, encoding="LDPC"):
    """
    根据符号数逆向计算 Wi-Fi 帧的数据长度 (Length)
    
    :param protocol: 'n', 'ac', 'ax', 'be'
    :param bw_mhz: 带宽 (20, 40, 80, 160, 320)
    :param n_sym: 观测到的符号个数
    :param mcs: MCS 索引
    :param n_ss: 空间流数
    :param encoding: "BCC" 或 "LDPC"
    :return: 最大可能的字节长度 (int)
    """
    
    # 1. 物理层子载波映射 (N_SD)
    nsd_table = {
        'ht':  {20: 52, 40: 108},
        'vht': {20: 52, 40: 108, 80: 242, 160: 484},
        'he': {20: 242, 40: 484, 80: 996, 160: 1992},
        'eht': {20: 242, 40: 484, 80: 996, 160: 1992, 320: 3984}
    }
    
    # 2. MCS 映射 (N_BPSCS, Rate)
    mcs_table = {
        0: (1, 1/2), 1: (2, 1/2), 2: (2, 3/4), 3: (4, 1/2),
        4: (4, 3/4), 5: (6, 2/3), 6: (6, 3/4), 7: (6, 5/6),
        8: (8, 3/4), 9: (8, 5/6), 10: (10, 3/4), 11: (10, 5/6),
        12: (12, 3/4), 13: (12, 5/6) # Wi-Fi 7 (4096QAM) 示例
    }

    try:
        n_sd = nsd_table[protocol.lower()][bw_mhz]
        n_bpscs, rate = mcs_table[mcs]
    except KeyError:
        return "错误：不支持的协议配置组合。"

    # 3. 计算每个符号承载的物理层数据位 (N_DBPS)
    n_dbps = n_sd * n_bpscs * n_ss * rate

    # 4. 计算总承载比特 (除去 Service 和 Tail 位)
    # 计算公式逆向：n_bits = n_sym * n_dbps
    total_payload_bits = n_sym * n_dbps
    
    service_bits = 16
    tail_bits = 6 if encoding.upper() == "BCC" else 0
    
    # 5. 换算回字节
    # 实际有效数据长度 = (总比特 - 物理层开销) / 8
    # 这里使用 floor 是因为 n_sym 是向上取整得来的，
    # 实际 Data 可能比 total_payload_bits 略小
    raw_length_bytes = (total_payload_bits - service_bits - tail_bits) / 8
    
    return int(math.floor(raw_length_bytes))

# --- 测试示例 ---
if __name__ == "__main__":
    print("--- Wi-Fi 帧长计算器 ---")
    
    # 示例 1:                                format  bw_mhz, n_sym, mcs, n_ss, encoding
    len_frame = calculate_wifi_payload_length('he',    80,   320  , 0,    1, "LDPC")
    print(f"估算最大长度: {len_frame} Bytes")

