import math

# 修正后的原函数
def he_tsym_para_gen(wifi_format='hesu', giltf=0):
    # hesu/heer giltf = 0: 1x + 0.8u(un-support)
    #          giltf = 1: 2x + 0.8u
    #          giltf = 2: 2x + 1.6u
    #          giltf = 3: 4x + 3.2u

    # hetb      giltf = 0: 1x + 1.6u(un-support)
    #          giltf = 1: 2x + 1.6u   heltf_sym_len=8, data-sym = 14.4
    #          giltf = 2: 4x + 3.2u   heltf_sym_len=16, data_sym = 16

    he_sym_len_dic = {
        0: 13.6,
        1: 13.6,  # 0.8GI
        2: 14.4,  # 1.6GI
        3: 16     # 3.2GI
    }

    heltf_sym_len_dic = {
        0: 7.2,
        1: 7.2,
        2: 8,
        3: 16
    }

    if (wifi_format == 'hetb'):
        tsym_data = he_sym_len_dic.get(giltf + 1, 16)
        tsym_heltf = heltf_sym_len_dic.get(giltf + 1, 16)
    else:
        tsym_data = he_sym_len_dic.get(giltf, 16)
        tsym_heltf = heltf_sym_len_dic.get(giltf, 7.2)

    return tsym_data, tsym_heltf

def hetb_para_gen(ru_size=26, Nss=1, mcs='mcs0', apep_length=0, num_heltf=1, nominal_pe=0, giltf=0,
                  run_mode='normal', nsym_regr_list=[1], he_afactor_regr_list=[1], list_index=0, trig_dcm_on=0,
                  trig_dpl_on=0, trig_mid=0, trig_fec_coding=0, trig_ldpcextra=1):
    ##list_index -> select rerun nsym and afactor
    # Nsym,tpe,t_pe_disambiguity,eof_padding_num,pre_fec_padding,post_fec_padding,apep_length_sta;

    # hetb      giltf = 0: 1x + 1.6u(un-support)
    #          giltf = 1: 2x + 1.6u
    #          giltf = 2: 4x + 3.2u

    nsym_basic_list_ru26 = [1, 2]
    nsym_basic_list_ru52 = [2, 3]
    nsym_basic_list_ru106 = [3, 4]
    nsym_basic_list_ru242 = [4, 5]
    nsym_basic_list_ru484 = [5, 6]
    nsym_basic_list_ru996 = [6, 7]
    nsym_basic_list_ru2x996 = [7, 8]

    he_afactor_basic_list_ru26 = [1, 2]
    he_afactor_basic_list_ru52 = [1, 2]
    he_afactor_basic_list_ru106 = [1, 3]
    he_afactor_basic_list_ru242 = [3, 4]
    he_afactor_basic_list_ru484 = [3, 4]
    he_afactor_basic_list_ru996 = [3, 4]
    he_afactor_basic_list_ru2x996 = [3, 4]

    if (ru_size == 26):
        nsym_basic_list = nsym_basic_list_ru26
        he_afactor_basic_list = he_afactor_basic_list_ru26
    elif (ru_size == 52):
        nsym_basic_list = nsym_basic_list_ru52
        he_afactor_basic_list = he_afactor_basic_list_ru52
    elif (ru_size == 106):
        nsym_basic_list = nsym_basic_list_ru106
        he_afactor_basic_list = he_afactor_basic_list_ru106
    elif (ru_size == 242):
        nsym_basic_list = nsym_basic_list_ru242
        he_afactor_basic_list = he_afactor_basic_list_ru242
    elif (ru_size == 484):
        nsym_basic_list = nsym_basic_list_ru484
        he_afactor_basic_list = he_afactor_basic_list_ru484
    elif (ru_size == 996):
        nsym_basic_list = nsym_basic_list_ru996
        he_afactor_basic_list = he_afactor_basic_list_ru996
    elif (ru_size == '2x996'):
        nsym_basic_list = nsym_basic_list_ru2x996
        he_afactor_basic_list = he_afactor_basic_list_ru2x996
    else:
        nsym_basic_list = nsym_basic_list_ru26
        he_afactor_basic_list = he_afactor_basic_list_ru26

    Nsd_dic = {
        26: 24,
        52: 48,
        106: 102,
        242: 234,
        484: 468,
        996: 984,
        '2x996': 1968
    }

    # un-support dcm
    Nsd_short_dic = {
        26: 6,
        52: 12,
        106: 24,
        242: 60,
        484: 120,
        996: 240,
        '2x996': 480
    }

    Nbpscs_dic = {
        'mcs0': 1,
        'mcs1': 2,
        'mcs2': 2,
        'mcs3': 4,
        'mcs4': 4,
        'mcs5': 6,
        'mcs6': 6,
        'mcs7': 6,
        'mcs8': 8,
        'mcs9': 8,
        'mcs10': 10,
        'mcs11': 10
    }

    # code rate numerator
    code_rate_numer_dic = {
        'mcs0': 1,  # 1/2
        'mcs1': 1,  # 1/2
        'mcs2': 3,  # 3/4
        'mcs3': 1,  # 1/2
        'mcs4': 3,  # 3/4
        'mcs5': 2,  # 2/3
        'mcs6': 3,  # 3/4
        'mcs7': 5,  # 5/6
        'mcs8': 3,  # 3/4
        'mcs9': 5,  # 5/6
        'mcs10': 3, # 3/4
        'mcs11': 5  # 5/6
    }

    # code rate denominator
    code_rate_denom_dic = {
        'mcs0': 2,  # 1/2
        'mcs1': 2,  # 1/2
        'mcs2': 4,  # 3/4
        'mcs3': 2,  # 1/2
        'mcs4': 4,  # 3/4
        'mcs5': 3,  # 2/3
        'mcs6': 4,  # 3/4
        'mcs7': 6,  # 5/6
        'mcs8': 4,  # 3/4
        'mcs9': 6,  # 5/6
        'mcs10': 4, # 3/4
        'mcs11': 6  # 5/6
    }

    hetb_time_ltf_dic = {
        0: 4.8,
        1: 8,
        2: 16
    }

    if (trig_dcm_on == 1):
        Nsd = Nsd_dic.get(ru_size, 24) / 2
    else:
        Nsd = Nsd_dic.get(ru_size, 24)
    Nsd_short = Nsd_short_dic.get(ru_size, 6)
    Nbpscs = Nbpscs_dic.get(mcs, 1)

    code_rate_numer = code_rate_numer_dic.get(mcs, 1)
    code_rate_denom = code_rate_denom_dic.get(mcs, 2)

    Ncbps = Nsd * Nbpscs * Nss
    Ndbps = int(Ncbps * code_rate_numer / code_rate_denom)
    print(f"Ncbps:{Ncbps} ,code_rate_numer:{code_rate_numer} , code_rate_denom{code_rate_denom}")
    Ncbps_short = Nsd_short * Nss * Nbpscs
    Ndbps_short = int(Ncbps_short * code_rate_numer / code_rate_denom)

    # 修正：去掉self.，直接调用独立函数
    (tsym_data, tsym_heltf) = he_tsym_para_gen('hetb', giltf)  ##tsym_data,tsym_heltf

    #################### AP ######################
    t_he_preamble = float(4 + 8 + 8 + num_heltf * tsym_heltf)  # hetb 4 rl-sig + 8 he-siga  + 8 hestf + heltf....

    Nservice = 16
    if (trig_fec_coding == 0):
        fec_coding_ap = 'BCC'
        Ntail = 6
        ldpcextra_ap = 1  ##review later
    else:
        fec_coding_ap = 'LDPC'
        Ntail = 0
        ldpcextra_ap = trig_ldpcextra

    ul_length = 4096  # 初始值设为大于4095，进入循环

    while (int(ul_length) > 4095):

        apep_length_float = float(apep_length + 4)
        Nsym_init = math.ceil((8 * apep_length_float + Ntail + Nservice) / Ndbps)  ##float
        print(f"========apep_length_float:{apep_length_float} , Ntail:{Ntail} , Nservice:{Nservice} ,Ndbps:{Ndbps}")
        Nexcess = float((8 * apep_length_float + Ntail + Nservice) % Ndbps)

        if (Nexcess == 0):
            afactor_init = 4
        else:
            if (math.ceil(Nexcess / (Ndbps_short)) < 4):
                afactor_init = math.ceil(Nexcess / Ndbps_short)
            else:
                afactor_init = 4

        if (run_mode == 'basic'):
            Nsym_ap = nsym_basic_list[list_index]
            afactor_ap = he_afactor_basic_list[list_index]
        elif (run_mode == 'regression'):
            Nsym_ap = nsym_regr_list[list_index]
            afactor_ap = he_afactor_regr_list[list_index]
        else:
            Nsym_ap = Nsym_init  ##Nsym must greater or equal than Nsym_init
            afactor_ap = afactor_init

        if (nominal_pe == 0):
            tpe_ap = 0
        elif (nominal_pe == 8):
            if (afactor_ap <= 2):
                tpe_ap = 0
            elif (afactor_ap == 3):
                tpe_ap = 4
            else:
                tpe_ap = 8
        else:
            if (afactor_ap == 1):
                tpe_ap = 4
            elif (afactor_ap == 2):
                tpe_ap = 8
            elif (afactor_ap == 3):
                tpe_ap = 12
            elif (afactor_ap == 4):
                tpe_ap = 16

        if (trig_dpl_on == 1):
            the_ltf = hetb_time_ltf_dic.get(giltf, 0)
        else:
            the_ltf = 0

        if (trig_dpl_on == 1):
            if (trig_mid == 0):
                print("please check the trig_mid when trig_dpl on!!!")
                return False
            else:
                N_MA = max(0, math.ceil((Nsym_ap - 1) / trig_mid) - 1)
        else:
            N_MA = 0

        tsym_mid = N_MA * num_heltf * the_ltf

        txtime = 20 + t_he_preamble + Nsym_ap * tsym_data + tsym_mid + tpe_ap + 6  # +sigal extension

        t_pe_disambiguity_judge = tpe_ap + 4 * (math.ceil((txtime - 6 - 20) / 4) - ((txtime - 6 - 20) / 4))

        if (t_pe_disambiguity_judge >= tsym_data):
            t_pe_disambiguity = 1
        else:
            t_pe_disambiguity = 0
        print(f"hetb_prar_gen AP: txtime:{txtime} , t_he_preamble:{t_he_preamble} ,Nsym_ap:{Nsym_ap} ,tsym_data:{tsym_data}, tsym_mid:{tsym_mid} ,tpe_ap:{tpe_ap}")
        ul_length = math.ceil((float(txtime) - 6 - 20) / 4) * 3 - 3 - 2  # hetb ul-length
        print("hetb_prar_gen AP: computing ul_length: %d" % ul_length)

        if (int(ul_length) > 4095):
            apep_length = int(apep_length * 0.95)

    print("hetb_prar_gen AP: apep_length %d" % apep_length)
    print("hetb_prar_gen AP: Nsym_init %d" % Nsym_init)
    print("hetb_prar_gen AP: Nexcess %d" % Nexcess)
    print("hetb_prar_gen AP: afactor_init %d" % afactor_init)
    print("hetb_prar_gen AP: tpe_ap %d" % tpe_ap)
    print("hetb_prar_gen AP: Nsym_ap %d" % Nsym_ap)
    print("hetb_prar_gen AP: afactor_ap %d" % afactor_ap)
    print("hetb_prar_gen AP: fec_coding_ap %s" % fec_coding_ap)
    print("hetb_prar_gen AP: ldpcextra_ap %d" % ldpcextra_ap)

    ########################STA #######################
    ul_length_float = float(ul_length)
    Nsym_sta = int(((ul_length_float + 2 + 3) / 3 * 4 - t_he_preamble) / tsym_data) - t_pe_disambiguity
    tpe_sta = int((((ul_length_float + 2 + 3) / 3) * 4 - t_he_preamble - Nsym_sta * tsym_data) / 4) * 4

    if (afactor_ap == 4):
        Ndbps_last = Ndbps
        Ncbps_last = Ncbps
    else:
        Ndbps_last = afactor_ap * Ndbps_short
        Ncbps_last = afactor_ap * Ncbps_short

    psdu_length = int(((Nsym_sta - 1) * Ndbps + Ndbps_last - Nservice - Ntail) / 8)  # un-support stbc & ldpc
    psdu_length_resdu_bits = ((Nsym_sta - 1) * Ndbps + Ndbps_last - Nservice - Ntail) % 8

    apep_length_random_max = psdu_length - 4
    delta_padding = psdu_length - apep_length_float

    if (delta_padding < 4):  # < 4byte padding -> phy padding
        eof_padding_num = 0
        pre_fec_padding = int(delta_padding * 8 + psdu_length_resdu_bits)  # to phy byte -> bits
    else:
        if ((apep_length_float % 4) == 0):  ##apep length 4byte
            eof_padding_num = int(delta_padding)  # mac calculate eof padding subframe
            pre_fec_padding = int((delta_padding % 4) * 8 + psdu_length_resdu_bits)
        else:
            delta_padding_recom = delta_padding + (apep_length_float % 4) - 4
            eof_padding_num = int(delta_padding_recom)
            pre_fec_padding = int((eof_padding_num % 4) * 8 + psdu_length_resdu_bits)

    post_fec_padding = int(Ncbps - Ncbps_last)

    # 返回所有关键结果，方便测试验证
    return (Nsym_sta, tpe_sta, t_pe_disambiguity, eof_padding_num, pre_fec_padding, 
            post_fec_padding, afactor_ap, fec_coding_ap, ldpcextra_ap, ul_length, apep_length, Nsym_ap)

# 测试函数
def test_he_tsym_para_gen():
    """测试he_tsym_para_gen函数的核心场景"""
    print("="*50)
    print("开始测试 he_tsym_para_gen 函数")
    print("="*50)
    
    # 测试场景1: hetb格式 + 不同giltf值
    test_cases = [
        ('hetb', 0, (13.6, 7.2)),    # giltf=0 → giltf+1=1
        ('hetb', 1, (14.4, 8.0)),    # giltf=1 → giltf+1=2
        ('hetb', 2, (16.0, 16.0)),   # giltf=2 → giltf+1=3
        ('hesu', 0, (13.6, 7.2)),    # hesu格式 + giltf=0
        ('hesu', 3, (16.0, 16.0))    # hesu格式 + giltf=3
    ]
    
    for wifi_format, giltf, expected in test_cases:
        result = he_tsym_para_gen(wifi_format, giltf)
        status = "PASS" if result == expected else "FAIL"
        print(f"测试用例: wifi_format={wifi_format}, giltf={giltf}")
        print(f"预期结果: {expected}, 实际结果: {result}, 状态: {status}")
        print("-"*30)

def test_hetb_para_gen():
    """测试hetb_para_gen函数的核心场景"""
    print("="*50)
    print("开始测试 hetb_para_gen 函数")
    print("="*50)
    
    # # 测试场景1: 默认参数（ru_size=26, mcs0, giltf=0）
    # print("测试场景1: 默认参数")
    # result = hetb_para_gen()
    # print(f"返回结果: Nsym_sta={result[0]}, tpe_sta={result[1]}, ul_length={result[9]}")
    # print("-"*30)
    
    # # 测试场景2: 不同RU尺寸（ru_size=52）
    # print("测试场景2: RU尺寸=52, MCS=3")
    # result = hetb_para_gen(ru_size=52, mcs='mcs3')
    # print(f"返回结果: Nsym_sta={result[0]}, tpe_sta={result[1]}, ul_length={result[9]}")
    # print("-"*30)
    
    # 测试场景3: 不同giltf值（giltf=2）
    print("测试场景3: giltf=2, nominal_pe=8")
    result = hetb_para_gen(mcs= 'mcs0',apep_length=8000, giltf=2, nominal_pe=8)
    print(f"返回结果: Nsym_sta={result[0]}, tpe_sta={result[1]}, ul_length={result[9]}")
    print("-"*30)

# 执行测试
if __name__ == "__main__":
    # 先测试基础的参数生成函数
    test_he_tsym_para_gen()
    
    # 再测试核心的hetb参数生成函数
    test_hetb_para_gen()
    
    print("\n所有测试执行完成！")