import math

import matplotlib.pyplot as plt
from PIL.ImageOps import expand
from matplotlib.backends.backend_pdf import PdfPages
import os
# import openpyxl
import glob
import csv
from matplotlib.pyplot import MultipleLocator
import pandas as pd
import re
import numpy as np
import sys
from datetime import datetime

def fre_is_vld(fre=0):
    if((fre>-22.1 and fre < -21.8) or (fre>17.9 and fre < 18.1)
            or (fre>57.9 and fre < 58.1) ):
        return 0;
    else:
        return 1;

def spectrum_format(filelist):
    for m in range(0, len(filelist)):
        df = pd.read_csv(filelist[m], index_col=False)
        spectrumMargin_list = df['spectrumMarginDb']
        spectrumMarginOffsetFreqHz_list = df['spectrumMarginOffsetFreqHz']
        is11b = "11b" in filelist[m]
        #Judge is need to format
        if len(re.split(':| |\'', spectrumMargin_list[0]))==11:
            spectrumMargin_list_modfy = []
            spectrumMarginOffsetFreqHz_list_modify = []
            for i in range(0, len(spectrumMargin_list)):
                spectrumMargin = re.split(':| |\'', spectrumMargin_list[i])
                spectrumMargin_fre = re.split(':| |\'', spectrumMarginOffsetFreqHz_list[i])
                spectrumMargin_rewrite = []
                spectrumMargin_fre_rewrite = []
                if is11b:
                    for idex in range(1, 5):
                        spectrumMargin_rewrite.append(str(round(float(spectrumMargin[idex + 1]),2)))
                        spectrumMargin_fre_rewrite.append(str(round(float(spectrumMargin_fre[idex])/1e6, 2)))
                else:
                    for idex in range(1, 9):
                        spectrumMargin_rewrite.append(str(round(float(spectrumMargin[idex + 1]), 2)))
                        spectrumMargin_fre_rewrite.append(str(round(float(spectrumMargin_fre[idex]) / 1e6, 2)))
                spectrumMargin_list_modfy.append(spectrumMargin_rewrite)
                spectrumMarginOffsetFreqHz_list_modify.append(spectrumMargin_fre_rewrite)
            #Modify the spectrumMargin in a better format
            df['spectrumMarginDb'] = spectrumMargin_list_modfy
            df['spectrumMarginOffsetFreqHz'] = spectrumMarginOffsetFreqHz_list_modify
            df.to_csv(filelist[m], index=False)

def fltness_check(df):
    f = open(logpath, 'w')
    flatness_check_ok = 1
    for m in range(0, len(filelist)):
        #print('Flatness Check File:',filelist[m])
        df = pd.read_csv(filelist[m], index_col=False)
        min_flatness_margin = 100
        min_line = 0
        flatness_sum = 0
        flatness_num = 0
        is11b = "11b" in filelist[m]
        if not is11b:
            flatness_list = df['spectralFlatness_margin']
            for i in range(0, len(flatness_list)):
                flatness_all_fre = re.split(':| |\'', flatness_list[i])
                for idex in range(2, 6):
                    flatness_sum = flatness_sum + float(flatness_all_fre[idex])
                    flatness_num = flatness_num + 1
                    if float(flatness_all_fre[idex]) < 0:
                        log_info = 'Case ' + filelist[m] + ' flatness is Violation' + ':Line NO. is ' + str(i) + ',FlatnessMargin is '+flatness_all_fre[idex]+'\n'
                        f.write(log_info)
                        flatness_check_ok = 0
                    if float(flatness_all_fre[idex]) < min_flatness_margin:
                        min_line = i
                        min_flatness_margin = float(flatness_all_fre[idex])
            log_info = 'Case ' + filelist[m] + ':' + 'Min_flatness is :' + str(min_flatness_margin) + ',Line is:' + str(
                min_line) + 'Ave Flatness is:' + str(flatness_sum / flatness_num) + '\n'
            f.write(log_info)
    f.close()
    return flatness_check_ok

def spectrum_check(filelist,logpath):
    spectrum_format(filelist)
    f = open(logpath, 'w')
    spectrum_check_ok = 1
    for m in range(0, len(filelist)):
        df = pd.read_csv(filelist[m], index_col=False)
        spectrumMargin_list = df['spectrumMarginDb']
        spectrumMarginOffsetFreqHz_list = df['spectrumMarginOffsetFreqHz']
        min_spectrum_margin = 100
        min_line = 0
        min_spectrum_fre = 0
        is11b = "11b" in filelist[m]
        for i in range(0, len(spectrumMargin_list)):
            spectrumMargin = re.split(',|\'', spectrumMargin_list[i])
            spectrumMargin_fre = re.split(',|\'', spectrumMarginOffsetFreqHz_list[i])
            if is11b:
                for idex in range(1, 5):
                    if (float(spectrumMargin[3*(idex-1)+1]) < 0) and fre_is_vld(float(spectrumMargin_fre[3*(idex-1)+1])):
                        log_info = 'Case ' + filelist[m] + ' spectrumMargin is Violation' + ':Line NO. is ' + str(i) + ',SpectrumMargin is '+spectrumMargin[3*(idex-1)+1]+'\n'
                        f.write(log_info)
                        spectrum_check_ok = 0
                    #Find Min Spectrum Margin
                    if float(spectrumMargin[3*(idex-1)+1]) < min_spectrum_margin and fre_is_vld(float(spectrumMargin_fre[3*(idex-1)+1])):
                        min_line = i
                        min_spectrum_margin = float(spectrumMargin[3*(idex-1)+1])
                        min_spectrum_fre = spectrumMargin_fre[3*(idex-1)+1]
            else:
                for idex in range(1, 9):
                    if (float(spectrumMargin[3*(idex-1)+1]) < 0) and fre_is_vld(float(spectrumMargin_fre[3*(idex-1)+1])):
                        log_info = 'Case ' + filelist[m] + ' spectrumMargin is Violation' + ':Line NO. is ' + str(i) + ',SpectrumMargin is '+spectrumMargin[3*(idex-1)+1]+'\n'
                        f.write(log_info)
                        spectrum_check_ok = 0
                    if float(spectrumMargin[3*(idex-1)+1]) < min_spectrum_margin and fre_is_vld(float(spectrumMargin_fre[3*(idex-1)+1])):
                        min_line = i
                        min_spectrum_margin = float(spectrumMargin[3*(idex-1)+1])
                        min_spectrum_fre = spectrumMargin_fre[3*(idex-1)+1]
        log_info = 'Case ' + filelist[m] + ':' + 'Min_spectrum is :' + str(min_spectrum_margin) + ',Fre is :'+min_spectrum_fre+',Line is:'+str(min_line)+'\n'
        f.write(log_info)
    f.close()
    return spectrum_check_ok

def tx_power_check(filelist,logpath):
    f = open(logpath, 'w')
    tx_power_check_ok = 1
    for m in range(0, len(filelist)):
        #print('Flatness Check File:',filelist[m])
        df = pd.read_csv(filelist[m], index_col=False)
        real_power_list = df['power']
        target_power_list = df['tx_power_set(dBm)']
        df_power = df.loc[df['tx_power_set(dBm)'] >= -11]
        df_power = df_power.pivot_table(index=['tx_power_set(dBm)'], values='power')
        df_power_list = df_power['power']
        #print(filelist[m])
        #Check Average Tx Power
        for i in range(-11, 21):
            if abs(df_power_list[i]-i) > 1.1:
                tx_power_check_ok = 0
                log_info = '#Case ' + filelist[m] +' Tx Power is Violation' + ':Average Real Power is:'+str(df_power_list[i])+',Target Power is:'+str(i)+'\n'
                f.write(log_info)
        #Check Per Tx Power
        for i in range(0, len(real_power_list)):
            if abs(real_power_list[i]-target_power_list[i]) > 1.5 and target_power_list[i] >= -11 and target_power_list[i] <= 20:
                log_info = 'Case ' + filelist[m] + ' Tx Power is Violation' + ':Line NO. is ' + str(i) + ',Real Power is:'+str(real_power_list[i])+',Target Power is:'+str(target_power_list[i])+'\n'
                f.write(log_info)
    f.close()
    return tx_power_check_ok

def evm_check(filelist,logpath):
    f = open(logpath, 'w')
    evm_check_ok = 1
    dotb_evm_thr = -28.5
    nht_evm_thr = [-31.010875, -31.2145, -31.35675, -30.951875, -31.211375, -30.89125, -30.641625, -30.73025,
                   -30.757625, -30.678375, -30.451375, -30.39075, -30.196875, -30.2975, -30.464625, -30.576125,
                   -30.1115, -30.168125, -30.166125, -30.27925, -30.284125, -30.31125, -30.386625, -30.21075,
                   -29.977125, -30.13075, -29.798875, -29.915125, -29.123125, -28.882375, -28.730375, -27.52525]
    ht_evm_thr = [-28.942625, -29.1286875, -29.417875, -29.020625, -28.7541875, -28.944, -28.75, -28.9356875,
                  -28.622875, -28.7701875, -28.752625, -28.2193125, -28.565625, -28.4448125, -28.4701875, -28.799,
                  -28.3333125, -28.270375, -28.405, -28.4715, -28.381625, -28.314125, -28.330125, -28.2131875,
                  -28.2409375, -28.21525, -28.059125, -28.0821875, -27.6456875, -27.6005625, -27.441375, -27.3044375]
    ht_stbc_evm_thr = [-26.3745625, -26.2819375, -26.6016875, -26.548625, -25.8998125, -26.6765, -25.60725, -25.9490625,
                       -26.4313125, -25.64075, -25.6105, -25.794625, -26.0799375, -25.602125, -25.359125, -25.955125,
                       -25.7529375, -26.0264375, -26.0838125, -25.52225, -26.1220625, -25.9109375, -25.9366875,
                       -25.531875, -25.374875, -25.759125, -25.5424375, -25.5125625, -24.70075, -25.2420625, -24.870125,
                       -24.1723125]
    ht_nss2_evm_thr = [-26.5175, -26.121875, -26.048125, -26.361875, -26.48375, -26.0675, -25.84375, -26.1275,
                       -26.17625, -26.124375, -25.9425, -26.00125, -25.816875, -26.185625, -26.0725, -26.48625,
                       -25.53625, -25.978125, -25.856875, -26.070625, -25.8425, -25.763125, -26.120625, -25.63125,
                       -25.7625, -25.5725, -25.830625, -25.44125, -25.261875, -25.1025, -25.431875, -24.665625]
    vht_evm_thr = [-29.7653125, -29.7914375, -29.6251875, -29.6195, -29.35175, -29.38625, -29.2305625, -29.4614375,
                   -29.3555625, -28.7866875, -29.2880625, -28.7403125, -28.8983125, -28.69625, -29.34, -29.264125,
                   -29.0275, -28.99775, -28.7571875, -28.6151875, -28.76375, -28.5040625, -28.6788125, -28.7459375,
                   -28.7990625, -28.6343125, -28.775375, -28.767, -28.294875, -28.0594375, -27.64775, -26.77375]
    vht_stbc_evm_thr = [-29.6758125, -29.6521875, -29.490375, -29.318125, -29.352125, -29.30075, -29.0385625,
                        -29.0796875, -29.19, -28.975125, -28.76475, -28.901875, -28.8386875, -28.748875, -29.032625,
                        -28.767875, -28.736125, -28.720375, -28.623375, -28.87575, -28.69625, -28.5593125, -28.5825,
                        -28.5703125, -28.4769375, -28.4843125, -28.523875, -28.3341875, -27.605625, -27.5143125,
                        -27.6380625, -26.853]
    vht_nss2_evm_thr = [-29.0475, -29.13, -29.009375, -29.059375, -28.849375, -29.124375, -28.900625, -28.955,
                        -28.88375, -28.62375, -28.979375, -28.978125, -28.675625, -28.72875, -28.76, -28.8375, -28.7675,
                        -28.7025, -28.696875, -28.5725, -28.7375, -28.42125, -28.801875, -28.618125, -28.7575,
                        -28.255625, -28.145625, -28.333125, -27.795625, -27.598125, -27.8225, -27.254375]
    hesu_dcm0_evm_thr = [-27.82824375, -27.84134167, -27.77469792, -27.78252083, -27.7236375, -27.72351875,
                         -27.63832083, -27.67614167, -27.64326875, -27.532525, -27.49062083, -27.51912083, -27.46110417,
                         -27.4399375, -27.594625, -27.5523, -27.42649375, -27.38413333, -27.39658125, -27.38218542,
                         -27.35130417, -27.33280833, -27.32144583, -27.28179583, -27.22700417, -27.160425, -27.06504792,
                         -27.00144167, -26.62016042, -26.46196042, -26.36388333, -25.67566458]
    hesu_dcm1_evm_thr = [-27.55772778, -27.54622222, -27.43682778, -27.46723889, -27.27011111, -27.3058, -27.24121667,
                         -27.20588889, -27.15971111, -26.9679, -26.99682222, -26.86707222, -26.89676667, -26.86242222,
                         -27.02228889, -27.03678889, -26.80053889, -26.77781111, -26.76398889, -26.76745, -26.79389444,
                         -26.8214, -26.78579444, -26.74356111, -26.66036111, -26.68355556, -26.58400556, -26.48451667,
                         -26.14243333, -25.95796111, -26.00856667, -25.54563889]
    heer_dcm0_evm_thr = [-27.90002778, -27.83222917, -27.88645833, -27.96530556, -27.7873125, -27.83786111,
                         -27.76321528, -27.62466667, -27.78358333, -27.54145833, -27.62738194, -27.71778472,
                         -27.63450694, -27.57851389, -27.70700694, -27.65860417, -27.45985417, -27.54009028,
                         -27.43843056, -27.21688889, -27.202625, -27.1135, -27.08986111, -26.840625, -26.55157639,
                         -26.42517361, -26.05251389, -25.85963194, -25.24469444, -24.98752083, -25.46910417,
                         -25.21507639]
    heer_dcm1_evm_thr = [-27.58994444, -27.70893056, -27.36243056, -27.42016667, -27.36506944, -27.43522222,
                         -27.18398611, -27.17956944, -27.35245833, -26.96572222, -27.06229167, -26.86698611,
                         -26.97463889, -27.17044444, -27.02794444, -26.97918056, -26.69061111, -26.73794444,
                         -26.59881944, -26.57411111, -26.46665278, -26.22166667, -26.01972222, -25.87936111,
                         -25.66901389, -25.23754167, -24.95811111, -24.61125, -24.080875, -23.87569444, -24.32629167,
                         -24.30290278]
    hesu_stbc_evm_thr = [-27.6966, -27.69117083, -27.64517292, -27.66710625, -27.57392292, -27.57065, -27.51062083,
                         -27.52558958, -27.5057, -27.34054792, -27.33276875, -27.34978542, -27.31456458, -27.29088125,
                         -27.41482292, -27.39855417, -27.24890833, -27.24167292, -27.23134375, -27.22785, -27.19893542,
                         -27.14916875, -27.16895833, -27.17335417, -27.06065417, -26.97834792, -26.91981667,
                         -26.83195833, -26.4117375, -26.24627083, -26.22983333, -25.64011042]
    hesu_nss2_evm_thr = [-27.64604167, -27.65970833, -27.62214583, -27.63375, -27.60172917, -27.592, -27.53529167,
                         -27.56745833, -27.5385625, -27.4550625, -27.45427083, -27.40708333, -27.43508333, -27.41539583,
                         -27.47329167, -27.47639583, -27.37872917, -27.37608333, -27.37164583, -27.30972917,
                         -27.30972917, -27.26233333, -27.26889583, -27.22547917, -27.12116667, -27.04385417,
                         -26.96877083, -26.91220833, -26.57045833, -26.366125, -26.32135417, -25.68502083]

    for m in range(0, len(filelist)):
        #print('Flatness Check File:',filelist[m])
        df = pd.read_csv(filelist[m], index_col=False)
        power_list = df['tx_power_set(dBm)']
        df_evm = df.loc[df['tx_power_set(dBm)'] >= -11]
        df_evm_nss0_list = []
        df_evm_nss1_list = []
        evm_nss0_list = []
        evm_nss1_list = []
        df_evm_list = []
        is11b = "11b" in filelist[m]
        if 'nss2' in filelist[m]:
            evm_nss0_list = df['evm_nss0']
            evm_nss1_list = df['evm_nss1']
            df_evm = df_evm.pivot_table(index=['tx_power_set(dBm)'], values=['evm_nss0','evm_nss1'])
            df_evm_nss0_list = df_evm['evm_nss0']
            df_evm_nss1_list = df_evm['evm_nss1']
        else :
            evm_list = df['evm']
            df_evm = df_evm.pivot_table(index=['tx_power_set(dBm)'], values='evm')
            df_evm_list = df_evm['evm']
        #Check Average Tx Power
        for i in range(-11, 21):
            if 'nss2' in filelist[m]:
                if (df_evm_nss0_list[i] > ht_nss2_evm_thr[i+11] or df_evm_nss1_list[i] > ht_nss2_evm_thr[i+11]) and filelist[m] == 'ht_nss2.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM0 is:'+str(df_evm_nss0_list[i])+',EVM1 is:'+str(df_evm_nss1_list[i])+',Ref EVM is:'+str(ht_nss2_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif (df_evm_nss0_list[i] > vht_nss2_evm_thr[i+11] or df_evm_nss1_list[i] > vht_nss2_evm_thr[i+11]) and filelist[m] == 'vht_nss2.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM0 is:'+str(df_evm_nss0_list[i])+',EVM1 is:'+str(df_evm_nss1_list[i])+',Ref EVM is:'+str(vht_nss2_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif (df_evm_nss0_list[i] > hesu_nss2_evm_thr[i+11] or df_evm_nss1_list[i] > hesu_nss2_evm_thr[i+11]) and filelist[m] == 'hesu_nss2.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM0 is:'+str(df_evm_nss0_list[i])+',EVM1 is:'+str(df_evm_nss1_list[i])+',Ref EVM is:'+str(hesu_nss2_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
            else:
                if df_evm_list[i] > dotb_evm_thr and is11b:
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] + ' EVM is Violation' + ':EVM is:' + str(df_evm_list[i]) + ',Ref EVM is:' + str(dotb_evm_thr) + ',Power is :' + str(i) + '\n'
                    f.write(log_info)
                elif df_evm_list[i] > nht_evm_thr[i+11] and filelist[m] == 'nht.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM is:'+str(df_evm_list[i])+',Ref EVM is:'+str(nht_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif df_evm_list[i] > ht_evm_thr[i+11] and filelist[m] == 'ht.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM is:'+str(df_evm_list[i])+',Ref EVM is:'+str(ht_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif df_evm_list[i] > ht_stbc_evm_thr[i+11] and filelist[m] == 'ht_stbc.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM is:'+str(df_evm_list[i])+',Ref EVM is:'+str(ht_stbc_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif df_evm_list[i] > vht_evm_thr[i+11] and filelist[m] == 'vht.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM is:'+str(df_evm_list[i])+',Ref EVM is:'+str(vht_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif df_evm_list[i] > vht_stbc_evm_thr[i+11] and filelist[m] == 'vht_stbc.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM is:'+str(df_evm_list[i])+',Ref EVM is:'+str(vht_stbc_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif df_evm_list[i] > hesu_dcm0_evm_thr[i+11] and filelist[m] == 'hesu_dcm0.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM is:'+str(df_evm_list[i])+',Ref EVM is:'+str(hesu_dcm0_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif df_evm_list[i] > hesu_dcm1_evm_thr[i+11] and filelist[m] == 'hesu_dcm1.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM is:'+str(df_evm_list[i])+',Ref EVM is:'+str(hesu_dcm1_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif df_evm_list[i] > heer_dcm0_evm_thr[i+11] and filelist[m] == 'heer_dcm0.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM is:'+str(df_evm_list[i])+',Ref EVM is:'+str(heer_dcm0_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif df_evm_list[i] > heer_dcm1_evm_thr[i+11] and filelist[m] == 'heer_dcm1.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM is:'+str(df_evm_list[i])+',Ref EVM is:'+str(heer_dcm1_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
                elif df_evm_list[i] > hesu_stbc_evm_thr[i+11] and filelist[m] == 'hesu_stbc.csv':
                    evm_check_ok = 0
                    log_info = '#Case ' + filelist[m] +' EVM is Violation' + ':EVM is:'+str(df_evm_list[i])+',Ref EVM is:'+str(hesu_stbc_evm_thr[i+11])+',Power is :'+ str(i)+'\n'
                    f.write(log_info)
        #Check Per Tx Power
        for i in range(0, len(power_list)):
            if 'nss2' in filelist[m]:
                if (evm_nss0_list[i] > -23 or evm_nss1_list[i] > -23) and power_list[i] >= -11 and power_list[i] <= 20 :
                    log_info = 'Case ' + filelist[m] + ' EVM is Violation' + ':Line NO. is ' + str(i) + ',EVM0 is:' + str(evm_nss0_list[i]) + ',EVM1 is:' + str(evm_nss1_list[i])+',Power is:' + str(power_list[i]) + '\n'
                    f.write(log_info)
            elif evm_list[i] > -23 and power_list[i] >= -11 and power_list[i] <= 20:
                log_info = 'Case ' + filelist[m] + ' EVM is Violation' + ':Line NO. is ' + str(i) + ',EVM is:'+str(evm_list[i])+',Power is:'+str(power_list[i])+'\n'
                f.write(log_info)
    f.close()
    return evm_check_ok

def crc_check(filelist,logpath):
    f = open(logpath, 'w')
    crc_check_ok = 1
    for m in range(0, len(filelist)):
        df = pd.read_csv(filelist[m], index_col=False)
        crc_list = df['psdu_crc']
        rate_list = df['rate']
        hesu_nsts1_mcs8_perthr = 0.5
        hesu_nsts1_mcs9_perthr = 0.8
        hesu_mcs8_per = 0
        hesu_mcs9_per = 0
        if filelist[m] == 'hesu_dcm0.csv' or filelist[m] == 'hesu_stbc.csv' or filelist[m] == 'hesu_nss2.csv':
            df_mcs8 = df.loc[df['rate'] == 'mcs8']
            mcs8_err_counts = df_mcs8['psdu_crc'].value_counts()
            hesu_mcs8_per = mcs8_err_counts['Fail']/(mcs8_err_counts['Fail'] + mcs8_err_counts['Pass'])
            df_mcs9 = df.loc[df['rate'] == 'mcs9']
            mcs9_err_counts = df_mcs9['psdu_crc'].value_counts()
            hesu_mcs9_per = mcs9_err_counts['Fail'] / (mcs9_err_counts['Fail'] + mcs9_err_counts['Pass'])

        for i in range(0, len(crc_list)):
            if ((rate_list[i] != 'mcs8' and rate_list[i] != 'mcs9') and crc_list[i] == 'Fail') or hesu_mcs8_per > hesu_nsts1_mcs8_perthr or hesu_mcs9_per > hesu_nsts1_mcs9_perthr:
                crc_check_ok = 0
                log_info = 'Case ' + filelist[m] + ' CRC is Violation' + ':Line NO. is ' + str(i) +',MCS is '+rate_list[i]+'\n'
                f.write(log_info)
    f.close()
    return crc_check_ok

def tx_plot_and_analyse(logfile,save_filr):
    now = datetime.now()
    pdf_date_time = now.strftime("tx_pdf_%Y_%m_%d_%H%M")
    txt_date_time = now.strftime("tx_result_%Y_%m_%d_%H%M")

    folder_name = f"{pdf_date_time}.pdf"
    os.makedirs(os.path.dirname(save_filr), exist_ok=True)
    pp = PdfPages(save_filr + folder_name)
    for i in range(len(logfile)):
        #evm
        column_lengend = []
        reorder_column_evm = []
        #spec_margin
        spec_marg_column_lengend_nss1 = []
        spec_marg_column_lengend_nss2 = []
        reorder_column_spec_marg_nss1 = []
        reorder_column_spec_marg_nss2 = []
        #iqimbalance
        iqimbalance_column_lengend = []
        reorder_column_iqimbalance = []
        #flatness
        flatness_column_lengend = []
        reorder_column_flatness = []


        #pre process
        print("File is ",logfile[i])
        x1 = plt.figure(dpi=64, figsize=(14, 60))
        df = pd.read_csv(logfile[i], index_col=False)
        if '--' != df['amplitude_imbalace'][0]:
            amp_sq = np.power(df['amplitude_imbalace']/100,2)
            phase_sq = np.power(df['phase_imbalance']*3.14/180,2)
            sum_sq = amp_sq + phase_sq
            sum_sq_safe = np.where(sum_sq <= 0 , 0.01 , sum_sq)
            df['IQImbalance'] = 10 * np.log10(sum_sq_safe) - 6
            #df['IQImbalance'] = 10*np.log10(np.power(df['amplitude_imbalace']/100,2)+np.power(df['phase_imbalance']*3.14/180,2)) - 6
        #if '--' != df['spectrumMarginDb'][0]:
        #    df['worstSpecMargin'] = df['spectrumMarginDb'].map(lambda x: min(x.split(':')[1].split('\'')[0].split(' '), key=float))
        if '--' != df['spectrumMarginDb_nss1'].iloc[0] :
            def calculate_worst_spec_margin(x):
                if x == '--' or pd.isna(x):
                    print(f"Warning: {logfile[i]} : spectrumMarginDb value is '--' for a row, skipping worstSpecMargin calculation.")
                    return np.nan
                try:
                    value_part = str(x).split(':')[1].split('\'')[0]
                    valid_values = [
                        float(val) for val in value_part.split(' ')
                        if val.strip() and val.replace('-', '').replace('.', '').isdigit()
                    ]  
                    if valid_values:
                        return min(valid_values, key=float)
                    
                    else:
                        print(f"Warning: {logfile[i]} : No valid numeric values found in spectrumMarginDb for a row, skipping. value is :{value_part} \n")
                        return np.nan
                except Exception as e:
                    print(f"Warning: {logfile[i]} : Failed to process spectrumMarginDb value '{x}'. Error: {str(e)}, skipping row.")
                    return np.nan
            df['worstSpecMargin_nss1'] = df['spectrumMarginDb_nss1'].apply(calculate_worst_spec_margin)  
        if '--' != df['spectrumMarginDb_nss2'].iloc[0] :
            df['worstSpecMargin_nss2'] = df['spectrumMarginDb_nss2'].apply(calculate_worst_spec_margin) 

        df['idx'] = df.index

        #flatness
        if 'spectralFlatness_margin' in df.columns:
            if '--' != df['spectralFlatness_margin'][0]:
                df['worstFlatnessMargin'] = df['spectralFlatness_margin'].map(lambda x: min(x.split(':')[1].split('\'')[0].split(' '), key=float) if '--' != x else x)
                table_flatness = pd.pivot_table(df, index=["idx"],values=["worstFlatnessMargin"])


        #power
        table_power = pd.pivot_table(df, index=["tx_power_set(dBm)"],values=["power"])

        #evm
        if 'evm_nss0' in df.columns:
            df['power'] = df['power'].map(lambda x: round(x))
            table_evm = pd.pivot_table(df, index=["tx_power_set(dBm)"], columns=["rate"], values=["evm_nss0","evm_nss1"])
            nss2_flag = " NSS2"
        else:
            df['power'] = df['power'].map(lambda x: round(x))
            table_evm = pd.pivot_table(df, index=["tx_power_set(dBm)"], columns=["rate"],values=["evm"])
            if 'Nsts' in df.columns:
                if int(df['Nsts'][0]) == 2 :
                    nss2_flag = " STBC"
                else :
                    nss2_flag = ""
            else:
                nss2_flag = ""

        columnlist = table_evm.columns

        for column in columnlist:
            column_lengend.append(column[1]+'_'+column[0])
        column_lengend.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))
        
        for column in column_lengend:
            for source_column in table_evm.columns:
                if 'evm_nss0' in df.columns:
                    if column.split('_')[0] == source_column[1] and column.split('_')[1] +'_' +column.split('_')[2] == source_column[0]:
                        reorder_column_evm.append(source_column)
                else:
                    if column.split('_')[0] == source_column[1].split('_')[0]:
                        reorder_column_evm.append(source_column)



        #worstSpecMargin
        if '--' != df['spectrumMarginDb_nss1'][0]:
            table_spec_marg_nss1 = pd.pivot_table(df, index=["tx_power_set(dBm)"],columns=["rate"],values=["worstSpecMargin_nss1"])

            spec_marg_columnlist_nss1 = table_spec_marg_nss1.columns
            for column in spec_marg_columnlist_nss1:
                spec_marg_column_lengend_nss1.append(column[1]+'_'+column[0])
            spec_marg_column_lengend_nss1.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))

            for column in spec_marg_column_lengend_nss1:
                for source_column in table_spec_marg_nss1.columns:
                    if column.split('_')[0] == source_column[1].split('_')[0]:
                        reorder_column_spec_marg_nss1.append(source_column)

        if '--' != df['spectrumMarginDb_nss2'][0]:
            table_spec_marg_nss2 = pd.pivot_table(df, index=["tx_power_set(dBm)"],columns=["rate"],values=["worstSpecMargin_nss2"])

            spec_marg_columnlist_nss2 = table_spec_marg_nss2.columns
            for column in spec_marg_columnlist_nss2:
                spec_marg_column_lengend_nss2.append(column[1]+'_'+column[0])
            spec_marg_column_lengend_nss2.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))

            for column in spec_marg_column_lengend_nss2:
                for source_column in table_spec_marg_nss2.columns:
                    if column.split('_')[0] == source_column[1].split('_')[0]:
                        reorder_column_spec_marg_nss2.append(source_column)

        
        #iqimbalance
        if '--' != df['amplitude_imbalace'][0]:
            table_iqimbalance = pd.pivot_table(df, index=["tx_power_set(dBm)"],columns=["rate"],values=["IQImbalance"])

            iqimbalance_columnlist = table_iqimbalance.columns
            for column in iqimbalance_columnlist:
                iqimbalance_column_lengend.append(column[1]+'_'+column[0])
            iqimbalance_column_lengend.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))

            for column in iqimbalance_column_lengend:
                for source_column in table_iqimbalance.columns:
                    if column.split('_')[0] == source_column[1].split('_')[0]:
                        reorder_column_iqimbalance.append(source_column)


        #case str
        case_str = logfile[i].split('_')[1] + '_' + logfile[i].split('_')[2] + '_' + logfile[i].split('_')[3] + '_' + logfile[i].split('_')[4] + " " + nss2_flag
        case_str = case_str.replace('[\'', '').replace('\']', '')


        folder_name = f"{txt_date_time}.txt"
        with open(save_file+folder_name, 'a') as f:

            original_stdout = sys.stdout
            sys.stdout = f
            base_columns = ['rate', 'wifi_format', 'tx_power_set(dBm)']
            new_columns = ['fec_coding'  ,'rf_chan' ,'short_gi']

            columns_to_print = base_columns.copy()
            for col in new_columns :
                if col in df.columns:
                    columns_to_print.append(col)

            print('****************************%s %s*******************************\n' % (case_str, nss2_flag))
            # ###check flatness
            if 'spectralFlatness_margin' in df.columns :
                if '--' != df['spectralFlatness_margin'][0]:
                    if '--' != df['spectralFlatness_margin'][0]:
                        if float(df['worstFlatnessMargin'].str.replace('--', '0').min()) < 0:
                            print(case_str + '      Flatness         Check    FAIL\n')
                            #print(df[['rate', 'wifi_format', 'tx_power_set(dBm)']][pd.to_numeric(df['worstFlatnessMargin'], errors='coerce') < 0])
                            print(df[columns_to_print][pd.to_numeric(df['worstFlatnessMargin'], errors='coerce') < 0])
                        else:
                            print(case_str + "      Flatness         Check    PASS")
                else:
                    print(case_str + "      Flatness         Check    NAN")
            else:
                print(case_str + "      Flatness         Check    NAN")



            
            #check worstSpecMargin
            if '--' != df['spectrumMarginDb_nss1'][0]:
                if float(df['worstSpecMargin_nss1'].min()) < 0  :
                    print(case_str + '      SpecMargin nss1  Check    FAIL\n')
                    
                    print(df[columns_to_print][pd.to_numeric(df['worstSpecMargin_nss1'], errors='coerce') < 0].to_string())
                    print("\n")
                else:
                    print(case_str + "      SpecMargin nss1  Check    PASS")

            if '--' != df['spectrumMarginDb_nss2'][0]:
                if float(df['worstSpecMargin_nss2'].min()) < 0  :
                    print(case_str + '      SpecMargin nss2  Check    FAIL\n')
                    print(df[columns_to_print][pd.to_numeric(df['worstSpecMargin_nss2'], errors='coerce') < 0].to_string())
                    print("\n")
                else:
                    print(case_str + "      SpecMargin nss2  Check    PASS")


            #check crc

            
            if 'Fail' in df['psdu_crc'].astype(str).value_counts():
                print(case_str +'      CRC                Check    FAIL\n')
                #print(df[['rate', 'wifi_format', 'tx_power_set(dBm)'] ,fec_coding][df['psdu_crc'] == 'Fail'].to_string())
                print(df[columns_to_print][df['psdu_crc'] == 'Fail'].to_string())
            else:
                print(case_str +'      CRC                Check    PASS')
            print("\n")
            sys.stdout = original_stdout

        #plot
        custom_colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#800000', '#008000',
                         '#000080', '#808000', '#F08080', '#8080F0', "#161A17", "#D6B315" , "#C43162" ]

        
        plt.subplot(6, 1, 1)
        plt.plot(table_power)
        plt.ylim([-15, 20])
        plt.xlim([-12, 20])
        plt.xlabel('ref_power (dBm)')
        plt.ylabel('real_power (dBm)')
        title_str = logfile[i].split('_')[1] + '_' + logfile[i].split('_')[2] + '_' + logfile[i].split('_')[3]  + '_' + logfile[i].split('_')[4]  + '_' + logfile[i].split('_')[5]  + '_' + logfile[i].split('_')[6] + '_'  + logfile[i].split('_')[7] + '_'  + logfile[i].split('_')[8] + '_'  + 'TxPower' + nss2_flag
        title_str = title_str.replace('[\'','').replace('\']','')
        plt.title(title_str)
        plt.grid()

        #iqimbalance
        if '--' != df['amplitude_imbalace'][0]:
            table_iqimbalance = table_iqimbalance[reorder_column_iqimbalance]
            plt.subplot(6, 1, 2)
            for j in range(len(table_iqimbalance.columns)):
                plt.plot(table_iqimbalance.index, table_iqimbalance[table_iqimbalance.columns[j]].values, 's-',color=custom_colors[int(j)])
            plt.plot(table_iqimbalance)
            plt.ylim([-70,-35])
            plt.xlim([-12, 20])
            plt.xlabel('ref_power (dBm)')
            plt.ylabel('IQ Imbalance (dB)')
            plt.legend(iqimbalance_column_lengend, bbox_to_anchor=(1, 1), loc=2, borderaxespad=0, numpoints=1, fontsize=8)
            title_str = logfile[i].split('_')[1] + '_' + logfile[i].split('_')[2] + '_' + logfile[i].split('_')[
                3]  + '_' + logfile[i].split('_')[4]  + '_' + logfile[i].split('_')[5]  + '_' + logfile[i].split('_')[6] + '_' + logfile[i].split('_')[7] + '_'  + logfile[i].split('_')[8] + '_' + 'IQ Imbalance'+ nss2_flag 
            title_str = title_str.replace('[\'','').replace('\']','')
            plt.title(title_str)
            plt.grid()


        #worstSpecMargin nss1
        if '--' != df['spectrumMarginDb_nss1'][0]:
            table_spec_marg_nss1 = table_spec_marg_nss1[reorder_column_spec_marg_nss1]
            plt.subplot(6, 1, 3)
            for j in range(len(table_spec_marg_nss1.columns)):
                plt.plot(table_spec_marg_nss1.index, table_spec_marg_nss1[table_spec_marg_nss1.columns[j]].values, 's-',color=custom_colors[int(j)])
            #plt.plot(table_spec_marg)
            plt.ylim([-10, 30])
            plt.xlim([-12, 20])
            plt.xlabel('ref_power (dBm)')
            plt.ylabel('Worst Spectrum Margin (dB)')
            plt.legend(spec_marg_column_lengend_nss1, bbox_to_anchor=(1, 1), loc=2, borderaxespad=0, numpoints=1, fontsize=8)
            title_str = logfile[i].split('_')[1] + '_' + logfile[i].split('_')[2] + '_' + logfile[i].split('_')[
                3] + '_' + logfile[i].split('_')[4]  + '_' + logfile[i].split('_')[5]  + '_' + logfile[i].split('_')[6] + '_' + logfile[i].split('_')[7] + '_'  + logfile[i].split('_')[8] + '_' + 'Worst Spectrum Margin'+ nss2_flag
            title_str = title_str.replace('[\'','').replace('\']','')
            plt.title(title_str)
            plt.grid()

        #worstSpecMargin nss2
        if '--' != df['spectrumMarginDb_nss2'][0]:
            table_spec_marg_nss2 = table_spec_marg_nss2[reorder_column_spec_marg_nss2]
            plt.subplot(6, 1, 4)
            for j in range(len(table_spec_marg_nss2.columns)):
                plt.plot(table_spec_marg_nss2.index, table_spec_marg_nss2[table_spec_marg_nss2.columns[j]].values, 's-',color=custom_colors[int(j)])
            #plt.plot(table_spec_marg)
            plt.ylim([-10, 30])
            plt.xlim([-12, 20])
            plt.xlabel('ref_power (dBm)')
            plt.ylabel('Worst Spectrum Margin nss2 (dB)')
            plt.legend(spec_marg_column_lengend_nss2, bbox_to_anchor=(1, 1), loc=2, borderaxespad=0, numpoints=1, fontsize=8)
            title_str = logfile[i].split('_')[1] + '_' + logfile[i].split('_')[2] + '_' + logfile[i].split('_')[
                3] + '_' + logfile[i].split('_')[4]  + '_' + logfile[i].split('_')[5]  + '_' + logfile[i].split('_')[6] + '_' + logfile[i].split('_')[7] + '_'  + logfile[i].split('_')[8] + '_' + 'Worst Spectrum Margin'+ nss2_flag
            title_str = title_str.replace('[\'','').replace('\']','')
            plt.title(title_str)
            plt.grid()

        #flatness
        if 'spectralFlatness_margin' in df.columns:
            if '--' != df['spectralFlatness_margin'][0]:
                plt.subplot(6, 1, 5)
                plt.plot(table_flatness)
                plt.ylim([0, 10])
                # plt.xlim([-12, 20])
                plt.xlabel('Case Index')
                plt.ylabel('Worst Flatness Margin (dB)')
                title_str = logfile[i].split('_')[1] + '_' + logfile[i].split('_')[2] + '_' + logfile[i].split('_')[
                    3]  + '_' + logfile[i].split('_')[4]  + '_' + logfile[i].split('_')[5]  + '_' + logfile[i].split('_')[6] + '_' + logfile[i].split('_')[7] + '_'  + logfile[i].split('_')[8] + '_' + 'Worst Flatness Margin'+ nss2_flag
                title_str = title_str.replace('[\'', '').replace('\']', '')
                plt.title(title_str)
                plt.grid()



        #evm
        table_evm = table_evm[reorder_column_evm]
        plt.subplot(6, 1, 6)
        for j in range(len(table_evm.columns)):
            if j%2 :
                plt.plot(table_evm.index, table_evm[table_evm.columns[j]].values, 'o-',color=custom_colors[int(j/2)])
            else:
                plt.plot(table_evm.index, table_evm[table_evm.columns[j]].values, 's-',color=custom_colors[int(j/2)])
        # plt.plot(table_evm)
        plt.ylim([-45, -18])
        plt.xlim([-12, 20])
        plt.xlabel('ref_power (dBm)')
        plt.ylabel('EVM (dB)')
        plt.legend(column_lengend, bbox_to_anchor=(1, 1), loc=2, borderaxespad=0, numpoints=1, fontsize=8)
        title_str = logfile[i].split('_')[1] + '_' + logfile[i].split('_')[2] + '_' + logfile[i].split('_')[
            3] + '_' + logfile[i].split('_')[4]  + '_' + logfile[i].split('_')[5]  + '_' + logfile[i].split('_')[6] + '_' + logfile[i].split('_')[7] + '_'  + logfile[i].split('_')[8] + '_' + 'EVM'+ nss2_flag
        title_str = title_str.replace('[\'', '').replace('\']', '')
        plt.title(title_str)
        plt.grid()
        pp.savefig(x1)
        plt.close(x1)




        ####result check ####
        #请在当前函数中调用fltness_check



    pp.close()
# os.chdir(r'D:/workspace/fpgaTxTest/20230704/mimo_len_check')
logfile = 'D:/chip_test/dev/chip_tx/eagletest/py_script_rls3p0_chip/Log/wifi_tx/260131/'
os.chdir(logfile)
save_file = 'D:/chip_test/dev/chip_tx/eagletest/py_script_rls3p0_chip/Log/wifi_tx/260131/result/'
# os.chdir(r'D:/workspace/fpgaTxTest/20240605/')
#os.chdir(r'D:/workspace/fpgaTxTest/20230704/mimo')
#flatness_log_file = 'D:/workspace/fpgaTxTest/tx_regress_log/tx_flatness_log.txt'
#spectrum_log_file = 'D:/workspace/fpgaTxTest/tx_regress_log/tx_spectrum_log.txt'
#tx_power_log_file = 'D:/workspace/fpgaTxTest/tx_regress_log/tx_power_log.txt'
#evm_log_file = 'D:/workspace/fpgaTxTest/tx_regress_log/tx_evm_log.txt'
#crc_log_file = 'D:/workspace/fpgaTxTest/tx_regress_log/tx_crc_log.txt'
my_files = sorted(glob.glob('risc*.csv'), key=os.path.getmtime)
#每个元素打印在不同的行
for file in my_files:
    print(file)


tx_plot_and_analyse(my_files,save_file)


# if fltness_check(my_files,flatness_log_file):
#     print("Flatness Check PASS.")
# else:
#     print("Flatness Check Fail.Please refer to the log for details.")

# if spectrum_check(my_files,spectrum_log_file):
#     print("Spectrum Check PASS.")
# else:
#     print("Spectrum Check Fail.Please refer to the log for details.")

# if tx_power_check(my_files,tx_power_log_file):
#     print("Tx Power Check PASS.")
# else:
#     print("Tx Power Check Fail.Please refer to the log for details.")

# if evm_check(my_files,evm_log_file):
#     print("EVM Check PASS.")
# else:
#     print("EVM Check Fail.Please refer to the log for details.")

# if crc_check(my_files,crc_log_file):
#     print("CRC Check PASS.")
# else:
#     print("CRC Check Fail.Please refer to the log for details.")


