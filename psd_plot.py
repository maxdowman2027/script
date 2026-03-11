import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
import openpyxl
import glob
import csv
import sys
from scipy.signal import welch
import re



# os.chdir(r'D:/chip_test/dev/chip_tx/eagletest/rftest_data/dump_node_200/260212/result')
# 支持 Windows 路径格式，自动处理路径分隔符
# 可以使用正斜杠(/)或反斜杠(\)作为路径分隔符
work_dir = r'D:\users\gxu\spur_scan\260310\dump_rx_data'
# 规范化路径，处理不同的路径分隔符
work_dir = os.path.normpath(work_dir)
os.chdir(work_dir)
FS = 80
csv_header = ["phy_mode", "channel", "frequency", "diff_pwr","pwr"]
# os.chdir(r'D:/workspace/fpgaRxTest/1222/Q_board_test'r'')
# freqMhz = 5180
# freqCw = 5140
mypath = os.getcwd()
print(mypath)
my_files = glob.glob('*.csv')
print(my_files[0])
# print(sheet.columns)
# bitwidth = 1
SPUR_THR = 18
legendList = [];
output_path = os.path.join(mypath , 'result')
csv_file_path = os.path.join(output_path,"spur_scan_result.csv") 
os.makedirs(output_path, exist_ok=True)

with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_header)
    writer.writeheader()
    f.closed
for m in range(0, len(my_files)):
    file_name = my_files[m]
    pattern = re.compile(r"(?:phy_mode(\d+))|(?:chan(\d+))", re.IGNORECASE)
    matches = pattern.findall(file_name)
    phy_mode_val = None
    chan_val = None
    # 遍历匹配结果，提取数字
    for name in matches:
        if name[0]:  # 第一个捕获组是phy_mode的数字
            phy_mode_val = int(name[0])
        if name[1]:  # 第二个捕获组是chan的数字
            chan_val = int(name[1])
    print(f"phymode{phy_mode_val}-chan{chan_val}")
    pp = PdfPages(f'{file_name}.pdf')
    with open(my_files[m], newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        k = 0
        data = [];
        for row in reader:
            # x = float(row[' sample i'])
            # y = float(row[' sample q'])
            keylist = list(row.keys())
            #x = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch1/u_host_data_mux/rx_i_fe_1_tmp[9:0]'])
            #y = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch1/u_host_data_mux/rx_q_fe_1_tmp[9:0]'])
            # x = float(row[' idata_ch0'])
            # y = float(row[' qdata_ch0 '])
            # if 'tx0' in my_files[m]:
            #     x = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch0/u_host_data_mux/rx_i_fe_fpga[9:0]'])
            #     y = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch0/u_host_data_mux/rx_q_fe_fpga[9:0]'])
            # else:
            #     x = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch1/u_host_data_mux/rx_i_fe_fpga_0[9:0]'])
            #     y = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch1/u_host_data_mux/rx_q_fe_fpga_0[9:0]'])
            # x = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch0/u_host_data_mux/rx_i_fe_0_tmp[9:0]'])
            # y = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch0/u_host_data_mux/rx_q_fe_0_tmp[9:0]'])
            # x = float(row['sample_i_ch0'])
            x = float(row[' sample i_ch0'])
            # y = float(row['sample_q_ch0'])
            y = float(row[' sample q_ch0'])
            # x = float(row['txsco_data[11:0]'])
            # y = float(row['sample_q_ch0'])
            # x = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch1/u_host_data_mux/rx_i_fe_1_tmp[9:0]'])
            # y = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch1/u_host_data_mux/rx_q_fe_1_tmp[9:0]'])
            # x = float(row['u_fpga_host_inf/u_host_mux_top_ch0/u_host_data_mux/fpga_modem_mimo_ch0_rx_i_fe[9:0]'])
            # y = float(row['u_fpga_host_inf/u_host_mux_top_ch0/u_host_data_mux/fpga_modem_mimo_ch0_rx_q_fe[9:0]'])
            # x = float(row['chip_top_inst/u_digital_wrap/u_hp_sys_top/u_modem_wrap/u_modem_top/u_wifi_bb_wrap/u_wifi_bb_top/u_rx_rxtime_top/u_rx_dfe_ctrl/u_sco_top/u_sco_0ch/u_interpolator_i/freq_buf_wr_data_0ch[23:12]'])
            # y = float(row['chip_top_inst/u_digital_wrap/u_hp_sys_top/u_modem_wrap/u_modem_top/u_wifi_bb_wrap/u_wifi_bb_top/u_rx_rxtime_top/u_rx_dfe_ctrl/u_sco_top/u_sco_0ch/u_interpolator_q/freq_buf_wr_data_0ch[11:0]'])
            data.append(complex(x, y))
            # data.append(complex(x, 0))
        #  rate=row['rate']
        # data = data[::2]
        #  print(rate)
        # legendList.append(rate)
        plt.close('all') 
        x1 = plt.figure();
        plt.plot(np.real(data), 'o-')
        plt.plot(np.imag(data), 'rs-')
        # plt.ylim([1e-s3,1])
        # plt.xlim([-100,-20])
        plt.ylabel('magintude')
        plt.xlabel('time sample')
        plt.title(my_files[m])
        plt.grid()
        Fs = FS
        # NFFT = Fs / 0.1
        NFFT = 16000
        overlap = NFFT / 2
        win = np.hanning(NFFT)
        # win = 16000
        [F, P] = welch(data, Fs, win, noverlap=overlap, nfft=NFFT, return_onesided=False, detrend=False)
        # print(f"P :{P}")
        x2 = plt.figure()
        indexed_arr = list(enumerate(P))
        # 按值降序排序（reverse=True）
        # sorted_arr = sorted(indexed_arr, key=lambda x: x[1], reverse=True)
        # # 取前5个（或全部，若长度不足5）
        # top5 = sorted_arr[:5] if len(sorted_arr) >=5 else sorted_arr
        # # 分离索引和值
        # top5_indices = [item[0] for item in top5]
        # top5_values = [item[1] for item in top5]
        # top5_F_values = []
        # print(f"top5_indices:{top5_indices}")
        # for i in top5_indices :
        #     top5_F_values.append(F[i])
        # print(f"top5_F_values:{top5_F_values}")
        result_indices = []
        for idx, value in enumerate(P):
            if (10 * np.log10(np.abs((value)))) > SPUR_THR:
                result_indices.append(idx)

        result_indices_f = []
        for fi, fv in enumerate(F):
            if np.abs(fv) == 1.0 :
                result_indices_f.append(fi)
        avg_pwr = 0        
        avg_pwr = ( (10 * np.log10(np.abs(( P[result_indices_f[0]] )))) + (10 * np.log10(np.abs(( P[result_indices_f[1]] )))) )/2
        print(f"avg_pwr is {avg_pwr}")
        SPUR_F = []
        POWER_List = []
        diff_pwr = []
        pwr = []
        for i in result_indices :
            if F[i]< -0.1 or F[i]> 0.1:
                if (chan_val > 14) :
                    if (chan_val + F[i] ) % 40 == 0:
                        SPUR_F.append(F[i])
                        POWER_List.append((10 * np.log10(np.abs((P[i])))))
                        # diff_pwr.append( round(((10 * np.log10(np.abs(P[i]))) - avg_pwr ) ,2))
                        pwr.append( round((P[i] -58) ,2))
                        pwr.append( round(((10 * np.log10(np.abs(P[i]))) - 58 ) ,2))
                else :
                    if chan_val == 14 and (2484+F[i]) % 40 == 0 :
                        SPUR_F.append(F[i])
                        POWER_List.append((10 * np.log10(np.abs((P[i])))))
                        diff_pwr.append( round(((10 * np.log10(np.abs((P[i])))) - avg_pwr ) ,2))
                        # pwr.append( round(((10 * np.log10(np.abs(P[i]))) - 58 ) ,2))
                        pwr.append( round((P[i] -58) ,2))
                    elif (2412 + 5*(chan_val - 1) + F[i] )%40 == 0 : 
                    # else : 
                        SPUR_F.append(F[i])
                        POWER_List.append((10 * np.log10(np.abs((P[i])))))  
                        diff_pwr.append( round(((10 * np.log10(np.abs((P[i])))) - avg_pwr ) ,2))      
                        # pwr.append( round(((10 * np.log10(np.abs(P[i]))) - 58 ) ,2))
                        print(f"spur_pwr :{P[i]}")
                        pwr.append( round((P[i] -58) ,2))           

        # print(f"SPUR_F is {SPUR_F} ,POWER is {POWER_List}")
                # 写入四组参数数据
        if len(SPUR_F) == 0:
            SPUR_F.append("no_spur")
            POWER_List.append("no_spur")
            diff_pwr.append('no_spur')
        param_dict = {}  # 空字典
        param_dict["phy_mode"] = phy_mode_val   
        param_dict["channel"] = chan_val    
        param_dict["frequency"] = SPUR_F
        param_dict["diff_pwr"] = diff_pwr
        param_dict["pwr"] = pwr

        with open(csv_file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=csv_header)
            writer.writerow(param_dict)
            f.closed     
        

        # # IQ Imbalance
        # power_pre = np.abs(np.fft.fftshift(P))
        # power_mirror_pre = power_pre[400 - 10 * (freqCw - freqMhz)]
        # power_main_pre = power_pre[400 + 10 * (freqCw - freqMhz)]
        # iQImbalance_pre = 10 * np.log10(power_mirror_pre / power_main_pre)
        # print("filename is %s, IQImbalance is: %f, power_mirror_pre is %f, power_main_pre is %f"% (plt.title(my_files[m]), iQImbalance_pre, 10 * np.log10(power_mirror_pre), 10 * np.log10(power_main_pre)))
        plt.plot(np.fft.fftshift(F), 10 * np.log10(np.abs(np.fft.fftshift(P))), 'b-')
        plt.title(my_files[m])
        # plt.legend(legendList,bbox_to_anchor=(0.8,0.9))
        # print(F)
        plt.xlabel('Freq(MHz)')
        plt.ylabel('power density (dB)')
        plt.grid()
        pp.savefig(x1)
        pp.savefig(x2)
        pp.close()
#print(len(my_files))

# plt.show()


