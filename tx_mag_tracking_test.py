from hal.common import MEM
from rftest.rflib.wifi_lib import WIFILIB
from hal.wifi_api import WIFIAPI
from rftest.testcase.wifi_performance.wifi_tx_test import WIFI_TX_TEST
import time
from rftest.tester_serv import tester
from rftest.utility.csv_report import csvreport
from hal.hwregister.hwreg.all import HWREG

# Cable Loss
# MEM:TABLE 'PATHLOSS_COMP';MEM:TABLE:DEFINE 'FREQ,LOSS'
# 5G: 9.2dB
# MEM:TABLE 'PATHLOSS_COMP';MEM:TABLE:INSert:POINt 5180MHz,9.2
# 2G: 6.5dB
# MEM:TABLE 'PATHLOSS_COMP';MEM:TABLE:INSert:POINt 2462MHz,6.5
# VSA1;RFC:USE 'PATHLOSS_COMP',RF1A

# Gain Table
# 0x600A909C [8:0] reg_gain_idx_cca_bitmap default value: 9'd234
# 0x600A9008 [26]  reg_agc_fix_gain_mode default value: 1'b0

'''
ADC Value have to in range -200 ~ 200
Attenuation with tx power index
LNA 1 --- 6dB
VGA 1 --- 1dB
default: 5G LNA 6 VGA 15; 2G LNA 4 VGA 27
tx power index     VGA Code        LNA Code
       0         +4(2G);+12(5G)  +2(2G);+1(5G)    
       4         +0(2G);+8(5G)   +2(2G);+1(5G)
       8              +4              +1
       12           default           +1
       16           default         default
       20           default         default
'''

'''
# AGC
VSA1;RLEVel:AUTO
VSA1;RLEV?
# Get EVM result
VSA1;init
WIFI
calc:txq 0,1
FETC:SEGM:OFDM:EVM:DATA:AVER?
'''
class wifi_tx_mag_track_test:
    def __init__(self, comport='', chipv='FPGA752'):
        self.comport = comport
        self.chipv = chipv
        self.mem = MEM(self.comport, self.chipv)
        self.wifi = WIFILIB(self.comport, self.chipv)
        self.wifiapi = WIFIAPI(self.comport, self.chipv)
        self.wifi_tx_test = WIFI_TX_TEST(self.comport, self.chipv, 'iqsxel')
        self.tester = tester.tester(tx_mag_track=1)
        self.HWREG = HWREG(self.comport, chipv)

    def read_gain_table(self):
        self.wifiapi.channel.req_com('CmdStop')
        time.sleep(0.02)
        gain_table = self.mem.rdm(0x600a909c, 8, 0)
        time.sleep(0.02)
        is_fixed = self.mem.rdm(0x600a9008, 26, 26)
        time.sleep(0.02)
        self.send_pkt()
        if is_fixed == 1:
            return gain_table
        else:
            return False

    def send_pkt(self):
        # tx packet 11G 6M
        self.wifiapi.channel.req_com('FillTxPacket 659360 4000 0 11 0 0 16 64 5 134 9 0')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('WifiTxStart 655371 0 5000 0 0 1 0 57350 16384')
        # tx packet he mcs0 ~3.7ms
        # self.wifiapi.channel.req_com('FillTxPacket_mimo 659360 4000 0 16 1 0 0 16 64 5 134 9 1')
        # time.sleep(0.2)
        # self.wifiapi.channel.req_com('WifiTxStart 655376 0 5000 0 0 1 1 2154503 16384')

    def close_track(self):
        self.wifiapi.channel.req_com('CmdStop')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('phy_tx_mag_ctrl_set 0 0 0 0 1 0 0')
        time.sleep(0.2)
        self.send_pkt()

    def open_track(self):
        self.wifiapi.channel.req_com('CmdStop')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('phy_tx_mag_ctrl_set 1 1 0 0 1 0 0')
        time.sleep(0.2)
        self.send_pkt()

    def dump_en(self, dump_node):
        self.mem.wrm(0x600a801c, 0, 0, 1)
        self.mem.wrm(0x600a8014, 0, 0, 1)
        self.mem.wrm(0x600a8010, 14, 14, 0)
        self.mem.wrm(0x600a8010, 13, 12, 0)
        self.mem.wrm(0x600a8010, 11, 0, dump_node)
        self.mem.wrm(0x600a8010, 31, 16, 3)

    def adjust_txpwr(self, txpwridx=20):
        self.wifiapi.channel.req_com('CmdStop')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('phy_dpd_calibration_top_fpga 20 1325 1349 1 1 8000 100 11 8 2000 6000 2 0 7000 32 32 %d 9' % txpwridx)
        time.sleep(0.2)
        self.send_pkt()

    def fix_dg3(self, bypass=0, dg3_en=0, dg3=0):
        self.wifiapi.channel.req_com('CmdStop')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('phy_tx_mag_dg3_set %d %d %d 0 0 0' %(bypass, dg3_en, dg3))
        time.sleep(0.2)
        self.send_pkt()

    def reset(self, chan=5180, lna5g=6, vga5g=15, lna2g=4, vga2g=27, win_len=64, start_mode=0, wait_len=300, start_point=1500, dly=54, txpwr=20, dg3_force=0, data_sel_thr=63, gain_comp=0, is_high_abs=0):
        # shift bit map
        if win_len <= 64:
            win_len_shift = 0
        elif win_len <= 128:
            win_len_shift = 1
        elif win_len <= 256:
            win_len_shift = 2
        elif win_len <= 512:
            win_len_shift = 3
        elif win_len <= 1024:
            win_len_shift = 4
        elif win_len <= 2048:
            win_len_shift = 5
        elif win_len <= 4096:
            win_len_shift = 6
        else:
            win_len_shift = 7
        # for gain comp debug
        # win_len_shift = win_len_shift - 2 if win_len_shift > 1 else 0
        print(f"win_len_shift is {win_len_shift}")

        # Constraints
        mag_track_ch_length = 130
        mag_track_ch0_offset = 5
        mag_track_ch1_offset = 5
        rx_dc_est_len_idx = 3
        dc_est_ch0_ofs = 100
        dc_est_ch1_ofs = 100
        # Constrain 1
        if start_point < (10 + (2 ** (rx_dc_est_len_idx + 7)) + dc_est_ch0_ofs + dc_est_ch1_ofs):
            start_point = 20 + (2 ** (rx_dc_est_len_idx + 7)) + dc_est_ch0_ofs + dc_est_ch1_ofs
            print(f"Update start_point to {start_point}")
        # Constrain 2
        if mag_track_ch_length < (win_len + 128):
            mag_track_ch_length = win_len + 256
            print(f"Update mag_track_ch_length to {mag_track_ch_length}")
        # Constrain 3
        if wait_len < (10 + 2 * mag_track_ch_length + mag_track_ch0_offset + mag_track_ch1_offset):
            wait_len = 20 + 2 * mag_track_ch_length + mag_track_ch0_offset + mag_track_ch1_offset
            print(f"Update wait_len to {wait_len}")

        # Update LNA VGA Gain based on txpwr
        # Add attenuator
        # if txpwr < 4:
        #     lna5g = 7
        #     vga5g = 27
        #     lna2g = 6
        #     vga2g = 31
        # elif txpwr < 8:
        #     lna5g = 7
        #     vga5g = 23
        #     lna2g = 6
        #     vga2g = 27
        # elif txpwr < 12:
        #     lna5g = 7
        #     vga5g = 19
        #     lna2g = 5
        #     vga2g = 31
        # elif txpwr < 16:
        #     lna5g = 7

        # No attenuator
        # if txpwr < 4:
        #     lna5g = 7
        #     vga5g = 27
        #     lna2g = 6
        #     vga2g = 31
        # elif txpwr < 8:
        #     lna5g = 7
        #     vga5g = 24
        #     lna2g = 6
        #     vga2g = 27
        # elif txpwr < 12:
        #     lna5g = 7    # lna5g = 7
        #     vga5g = 18   # vga5g = 18
        #     lna2g = 5
        #     vga2g = 31
        # elif txpwr < 16:
        #     lna5g = 7
        # elif txpwr < 20:
        #     vga5g = 14


        if chan < 20:
            print(f"LNA Code is {lna2g}, VGA Code is {vga2g}")
        else:
            print(f"LNA Code is {lna5g}, VGA Code is {vga5g}")

        self.wifiapi.channel.req_com('CmdStop')
        self.wifiapi.channel.req_com('wr 0x600a881c 0x2800000')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('wr 0x600a881c 0x2800000')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('wr 0x6009f0cc 0x1020')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('wr 0x6009f0cc 0x1020')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('wr 0x600a0c64 0xfff')
        time.sleep(0.2)
        # frame_end mode cofig
        # self.wifiapi.channel.req_com('wr 0x600a8818 0x7000')
        # time.sleep(0.2)

        self.wifiapi.channel.req_com('RFChannelSel %d 0' % chan)
        time.sleep(10)
        self.wifiapi.channel.req_com('enableTxRxIqModel 0 0')
        time.sleep(0.2)
        if is_high_abs:
            self.mem.wrm(0x600a88a4, 8, 8, 1)
        else:
            self.mem.wrm(0x600a88a4, 8, 8, 0)
        if chan < 20:
            self.wifiapi.channel.req_com('phy_iq_setting %d %d 1 0 127 7 20 0' % (lna2g, vga2g))
            time.sleep(0.2)
        else:
            self.wifiapi.channel.req_com('phy_iq_setting %d %d 1 0 127 7 20 1' % (lna5g, vga5g))
            time.sleep(0.2)

        # self.wifiapi.channel.req_com(
        #     'phy_tx_mag_dc_len_set %d %d %d' % (dc_est_ch0_ofs, dc_est_ch1_ofs, 0))
        # time.sleep(0.2)
        # self.wifiapi.channel.req_com('phy_tx_mag_dc_ctrl 0 0 0 1 0 1 1')
        # time.sleep(0.2)

        # New config
        self.wifiapi.channel.req_com(
            'phy_tx_mag_pow0_set 1 %d %d %d %d' % (mag_track_ch_length, win_len, win_len_shift, wait_len))
        # New Version
        dly_res = self.wifiapi.channel.req_com('phy_dpd_calibration_top_fpga 20 1325 1349 1 1 8000 100 11 8 2000 6000 2 0 7000 128 128 %d 9' % txpwr)
        time.sleep(0.2)
        if gain_comp == 0:
            # TODO: open or close Gain Comp
            self.wifiapi.channel.req_com('phy_tx_mag_rx_gain_set 1 0 0 0 0 0 0')
            # self.wifiapi.channel.req_com('phy_tx_mag_rx_gain_set 0 0 0 0 0 0 0')
        else:
            self.wifiapi.channel.req_com('phy_tx_mag_rx_gain_set 0 1 %d 0 0 0 0' % gain_comp)
        time.sleep(0.2)
        if dg3_force == 0:
            self.wifiapi.channel.req_com('phy_tx_mag_dg3_set 0 0 0 0 0 0')
            time.sleep(0.2)
        else:
            res = self.wifiapi.channel.req_com('phy_tx_mag_dg3_set 0 1 %d 0 0 0' % dg3_force)
            print(f"dg3_force res is {res}")
            time.sleep(0.2)
        self.wifiapi.channel.req_com('phy_tx_mag_thres_set  0 0 0 0')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('phy_tx_mag_adc4x_ctrl 1')
        time.sleep(0.2)
        if chan < 20:
            self.wifiapi.channel.req_com('phy_tx_mag_dly_set %d %d %d' % (data_sel_thr, dly, dly))
            time.sleep(0.2)
        else:
            self.wifiapi.channel.req_com('phy_tx_mag_dly_set %d %d %d' % (data_sel_thr, dly, dly))
            time.sleep(0.2)
        # Old version
        # self.wifiapi.channel.req_com('phy_tx_mag_len_set %d %d %d %d 5 5 130' % (start_mode, wait_len, start_point, win_len))
        # New version
        self.wifiapi.channel.req_com('phy_tx_mag_len_set %d %d %d %d %d %d %d 0 0 %d' % (start_mode, wait_len, start_point, win_len, mag_track_ch0_offset, mag_track_ch1_offset, mag_track_ch_length, win_len_shift))
        print('phy_tx_mag_len_set %d %d %d %d %d %d %d 0 0 %d' % (start_mode, wait_len, start_point, win_len, mag_track_ch0_offset, mag_track_ch1_offset, mag_track_ch_length, win_len_shift))
        time.sleep(0.2)
        self.wifiapi.channel.req_com(
            'phy_tx_mag_dc_len_set %d %d %d' % (dc_est_ch0_ofs, dc_est_ch1_ofs, rx_dc_est_len_idx))
        time.sleep(0.2)
        # TODO: open or close DC comp
        self.wifiapi.channel.req_com('phy_tx_mag_dc_ctrl 1 1 1 1 0 1 1')
        # self.wifiapi.channel.req_com('phy_tx_mag_dc_ctrl 0 0 0 1 0 1 1')
        time.sleep(0.2)
        self.wifiapi.channel.req_com('phy_tx_mag_ctrl_set 1 1 0 0 1 0 0')
        time.sleep(0.2)
        # tx packet 11G 6M
        self.send_pkt()

    def get_evm(self, num=10, chan=5180):
        res = self.tester.tx_mag_tracking_res(num, chan)
        res = str.split(str(res), ',')
        evm = round(float(res[0]), 2)
        pwr = round(float(res[1]), 2)
        print(f"tx mag tracking evm is {evm}, pwr is {pwr}")
        return [evm, pwr]

    def tot_test(self, debug_mode=0, gain_comp=0):
        if debug_mode == 0:
            chan_list = [11, 5180]          # [11, 5180]
            start_mode_list = [0]
            dg3_list = [0]              # default is [0], not force dg3  example: list(range(496, 529, 2))
            win_len_list = list(range(512, 4097, 512))  # [2 ** i for i in range(9, 13)]    # power 2 2^6=64 2^12=4096
            tx_pwr_list = list(range(0, 21, 2))         # list(range(0, 21, 2))    # 0 ~ 20 step
            dly_base_list = list(range(-2, 3, 1))       #list(range(-2, 3, 1))  # -2 ~ +2
            dly_offset = 54
            dly_list = [dly_offset + i for i in dly_base_list]
            data_sel_thr_lst = [63]     # list(range(15, 64, 8))
        else:
            chan_list = [11]
            start_mode_list = [0]
            dg3_list = [0]  # default is [0], not force dg3   list(range(496, 529, 2))
            win_len_list = [64]  # list(range(512, 4097, 512))
            tx_pwr_list = [8]         # list(range(0, 21, 4))
            dly_base_list = list(range(0, 101, 10))
            dly_offset = 54
            dly_list = [dly_offset]    # [dly_offset + i for i in dly_base_list]
            data_sel_thr_lst = [63]
            lna2g = 5
            vga2g = 20
            is_high_abs = 1


        data_row = []
        avg_num = 20
        for chan in chan_list:
            for tx_pwr in tx_pwr_list:
                # tx mag track off
                self.reset(chan=chan, txpwr=tx_pwr, lna2g=lna2g, vga2g=vga2g)
                self.close_track()
                [evm, pwr] = self.get_evm(num=avg_num, chan=chan)
                data_row_tmp = [chan, 0, 0, tx_pwr, 0, 0, 0, 0, pwr, evm]
                data_row.append(data_row_tmp)
                for dg3 in dg3_list:
                    for start_mode in start_mode_list:
                        for win_len in win_len_list:
                            for dly in dly_list:
                                for data_sel_thr in data_sel_thr_lst:
                                    print(f"chan is {chan}, txpwr is {tx_pwr}, dg3 is {dg3}, start_mode is {start_mode}, win_len is {win_len}, dly is {dly}, data_sel_thr is {data_sel_thr}")
                                    # tx mag track on
                                    self.reset(chan=chan, start_mode=start_mode, win_len=win_len, txpwr=tx_pwr, dg3_force=dg3, dly=dly, data_sel_thr=data_sel_thr, lna2g=lna2g, vga2g=vga2g, gain_comp=gain_comp, is_high_abs=is_high_abs)
                                    [evm, pwr] = self.get_evm(num=avg_num, chan=chan)
                                    # save data to csv file
                                    data_row_tmp = [chan, start_mode, win_len, tx_pwr, dly, dg3, data_sel_thr, 1, pwr, evm]
                                    data_row.append(data_row_tmp)
        fname = "C:/Users/DELL/Desktop/gdw_res/mag_track_test_res/mag_track_test_res"
        title = 'chan, start_mode, win_len, tx_pwr, dly, dg3, data_sel_thr, tx_mag_track_on, pwr, evm\n'
        csvreport1 = csvreport(fname, title)
        for data in data_row:
            csvreport1.write_data(data)







    def txtest_normal_top(self, logpath='wifi_tx', para_set='default', loop_num=1, cap_num=1, cable_loss=2.8,
                          vsa_port=1, alys_offs=0, channel=[3], chan_sel='all', bss_bw=40, phy_mode=0, m20_position=0,
                          cbw=[0], wifi_format='hesu', rate_sym=['mcs7', 'mcs8', 'mcs9'], data_len_in=4000, ampdu_len=0,short_gi=0,
                          giltf=[1, 2, 3], nominal_pe=0, run_mode='normal', data_len_regr_list=[20],
                          pwr_chk_enb='pwr_chk_disable', tx_power_fix=list(range(-15, 21)), tx_shr=0, bb_scale_enb=0,
                          dcm_on_enb=[0], dpl_on_enb=[0], mid_enb=[0], mode_11p=0, shortlog=0, afactor_scan=0,
                          target_afactor=[4], pathloss_comp_on=0, fec_coding=0, scr_seed_lst=['default', [1]],
                          frm_gap=5000, mimo_siso_mode='siso', nsts=1, stbc=0, ru106=0,
                          ant_sel=1):  ##dcm_on=0,vsg_dpl_on=0,vsg_mid=0
        ##used to check non_ax/hesu/heer/
        ##mode_11p=0 : normal 11g  / mode_11p=1  10MHz  / mode_11p=2 5MHz
        only_check = 0;
        verbose = 0;
        backoff_qdb = 0;
        frm_delay = frm_gap;
        dis_cca = 1;
        num_heltf = 1;
        cmd_stop = "cmd_stop",
        is_hesu_ru106 = ru106 & (wifi_format == 'heer')

        # for ht40
        ##self.HWREG.MAC_SCH.MACAUTOTXRX_ENA.reg_autotx_ena=1;
        ####self.HWREG.MAC_SCH.MACSRCONF.reg_sr_psr_based_ena=0;
        # self.HWREG.MAC_SCH.MACBB_INIT_VALUE.reg_bb_cca_ind_ht40_sec=2
        ##self.mem.wr(0x600A6c0c, 0)  # TODO

        # self.HWREG.BB.BB_FSM_CTRL.reg_tx_wait_delay=45;
        # self.HWREG.BB_TX.BB_BTX_NOISE_Q.reg_tx_interp_delay=32

        ## change the scramble ssed for temp
        ##        scr_seed = 1;
        ##        self.HWREG.BB_TX.BBTXCONF.reg_seed_load = 1;
        ##        self.HWREG.BB_TX.BBTXCONF.reg_seed = scr_seed;
        ##        print("!!!debug: the scramble seed is %d" %scr_seed)
        ## cfo bypass
        # self.HWREG.BB_TX.BBTX_CFO.reg_tx_cfo_sel = 0;

        ##         for c6 delay
        ##        self.mem.wr(0x600A7400,int(0x418e3a5))
        ##        self.mem.wr(0x600A7C00,int(0x7e0c041))
        ##        self.mem.wr(0x600A7C6C,int(0xc3378de))

        ####        for 32 delay
        # self.mem.wr(0x600A4C54,int(0x29e94000))
        # self.mem.wr(0x600A4C58,int(0xbd19d47))
        # self.mem.wr(0x600A7C6C,int(0xa5320c8))

        ## for apm secure
        ###-TBD--20221109--self.mem.wrm(0x600990C4,3,0,0)

        giltf_num_dic = {
            0: 'GILTF0',
            1: 'GILTF1',
            2: 'GILTF2',
            3: 'GILTF3'
        };

        wave_count = 10;
        #################TBD used to test scripts##############
        meas_type_11ag_list = ['psduCrcFail', 'plcpCrcPass', 'dataRate', 'numSymbols', 'numPsduBytes', 'dcLeakageDbc',
                               'evmAll', 'evmData', 'evmPilot', 'codingRate', 'freqErr', 'clockErr',
                               'ampErr', 'ampErrDb', 'phaseErr', 'rmsPhaseNoise', 'rmsPowerNoGap',
                               'rmsPower', 'pkPower', 'rmsMaxAvgPower', 'maskerr', 'on_time', 'off_time', 'maxrxpwr',
                               'spectrumAverViolationPercentage', 'spectrumAverObw', 'valid', 'length'
                               ];
        meas_type_11b_list = ['lockedClock', 'plcpCrcFail', 'psduCrcFail', 'longPreamble', 'numPsduBytes',
                              'bitRateInMHz',
                              'evmPk', 'bitRate', 'dataRate', 'modType', 'evmAll', 'evmInPreamble', 'evmInPsdu',
                              'freqErr',
                              'clockErr', 'ampErr', 'ampErrDb', 'phaseErr', 'rmsPhaseNoise', 'rmsPowerNoGap',
                              'rmsPower',
                              'pkPower', 'rmsMaxAvgPower', 'loLeakageDb', 'maskerr', 'on_time', 'off_time', 'maxrxpwr',
                              'spectrumAverViolationPercentage', 'spectrumAverObw', 'valid', 'length'
                              ];
        meas_type_11n_list = ['evmAvgAll', 'packetDetection', 'psduCRC', 'acquisition', 'demodulation', 'dcLeakageDbc',
                              'dcLeakageDbc',
                              'rxRmsPowerDb', 'isolationDb', 'freqErrorHz', 'symClockErrorPpm', 'PhaseNoiseDeg_RmsAll',
                              'IQImbal_amplDb',
                              'IQImbal_phaseDeg', 'rateInfo_bandwidthMhz', 'rateInfo_dataRateMbps',
                              'rateInfo_spatialStreams',
                              'analyzedRange', 'htSig1_htLength', 'htSig1_mcsIndex', 'htSig1_bandwidth',
                              'htSig2_advancedCoding',
                              'rateInfo_spaceTimeStreams', 'maxrxpwr', 'OBW_MHZ_VSA1',
                              'spectrumAverViolationPercentage', 'spectrumAverObw', 'valid', 'length'
                              ];
        meas_type_11ac_list = ['evmAvgAll', 'packetDetection', 'psduCRC', 'acquisition', 'demodulation', 'dcLeakageDbc',
                               'dcLeakageDbc',
                               'rxRmsPowerDb', 'isolationDb', 'freqErrorHz', 'symClockErrorPpm', 'PhaseNoiseDeg_RmsAll',
                               'IQImbal_amplDb',
                               'IQImbal_phaseDeg', 'rateInfo_bandwidthMhz', 'rateInfo_dataRateMbps',
                               'rateInfo_spatialStreams',
                               'analyzedRange', 'htSig1_htLength', 'htSig1_mcsIndex', 'htSig1_bandwidth',
                               'htSig2_advancedCoding',
                               'rateInfo_spaceTimeStreams', 'maxrxpwr', 'OBW_MHZ_VSA1',
                               'spectrumAverViolationPercentage', 'spectrumAverObw', 'valid', 'length'
                               ];
        meas_type_11ax_list = [
            'evmAvgAll', 'packetDetection', 'psduCRC', 'acquisition', 'demodulation', 'dcLeakageDbc',
            'rxRmsPowerDb', 'freqErrorHz', 'symClockErrorPpm', 'PhaseNoiseDeg_RmsAll', 'IQImbal_amplDb',
            'IQImbal_phaseDeg', 'rateInfo_bandwidthMhz', 'rateInfo_dataRateMbps', 'rateInfo_spatialStreams',
            'analyzedRange', 'rateInfo_spaceTimeStreams', 'maxrxpwr',
            'spectrumAverViolationPercentage', 'spectrumAverObw', 'valid', 'length',

            'Num_sig', 'Nsym', 'Num_tone', 'Lg_sig_crc', 'LTF_size', 'Afactor', 'he_pe',
            'MCS', 'fec_coding', 'Num_user', 'psdu_length', 'mu_ru_index', 'ru_size',
            'GI_value', 'staid'
        ];

        vect_type_11ag_list = ['hhEst', 'psdu', 'startPointers', 'plcp', 'spectrumMarginOffsetFreqHz',
                               'spectrumMarginDb_nss1', 'spectrumMarginDb_nss2','spectralFlatness_margin'];
        vect_type_11b_list = ['evmInPlcp', 'evmErr', 'spectrumMarginOffsetFreqHz', 'spectrumMarginDb_nss1', 'spectrumMarginDb_nss2',];
        vect_type_11n_list = ['channelEst', 'evmSymbols', 'evmTones', 'PhaseNoiseDeg_Symbols', 'demodSymbols',
                              'spectrumMarginOffsetFreqHz', 'spectrumMarginDb', 'spectralFlatness_margin'
                              ];
        vect_type_11ac_list = ['channelEst', 'evmSymbols', 'evmTones', 'PhaseNoiseDeg_Symbols', 'demodSymbols',
                               'spectrumMarginOffsetFreqHz', 'spectrumMarginDb_nss1', 'spectrumMarginDb_nss2', 'spectralFlatness_margin'
                               ];
        vect_type_11ax_list = ['channelEst', 'evmSymbols', 'evmTones', 'PhaseNoiseDeg_Symbols', 'demodSymbols',
                               'spectrumMarginOffsetFreqHz', 'spectrumMarginDb_nss1', 'spectrumMarginDb_nss2', 'spectralFlatness_margin'
                               ];

        #################TBD##############

        if False == os.path.exists('./log/%s' % logpath):
            try:
                os.makedirs(r'./log/%s' % logpath)
            except:
                logerror("Error: create directory %s failed!" % logpath)
                return False
        if cable_loss < 0:
            print("Error: the value of cable_loss should be nonnegative")
            return False
        (wififormat_list, chansel_num_list) = self.bssbw_wififormat_chansel_check(bss_bw, wifi_format, chan_sel)
        # print wififormat_list,chansel_num_list
        if wififormat_list == False:
            return False
        if chansel_num_list == False:
            return False
        if self.rfchan_check(channel, bss_bw) == False:
            return False
        if self.bssbw_wififormat_rate_check(bss_bw, wifi_format, rate_sym) == False:
            return False

        #### open test report for writing

        date_stamp = time.strftime('%Y-%m%d-%H%M%S', time.localtime())
        test_report = './log/wifi_tx/wifitx_%sm_%s_nss%d_stbc%d_fec_coding%d_channel%d_%s.csv' % (bss_bw, wifi_format, nsts,stbc,fec_coding , channel[0] ,date_stamp )

        print(("Info: test report file is %s" % test_report))
        fid = open(test_report, 'w')
        print("******************************MIMO SISO SET0***********************************")
        if only_check != 1:
            fid.write(
                'wifi_format, cbw, ht_dup, chan_sel, rate, data_len, short_gi,giltf,heltf_num,rf_chan, freq_tx, backoff(dB), cable_loss(dB), nominal_pe,spec,cbw,format,ana_sig,Nuser,Ntone,ru_index,ru_size,Nsts,afactor,shortgi,gi,pe,Nsym,fec_coding,mcs,coding_rate,data_rate,l_sig_crc,N_stf,he_ltf,sig_crc,psdu_length,psdu_crc,plcp_crc,sta_id,preamble_type,phase_err(deg),freq_err(Hz),sys_clk_err(ppm),LO_leakage(dB),evm_aver(dB),evm_max(dB),evm_min(dB),Rx_power_aver(dBm),Rx_power_max(dBm),Rx_power_min(dBm),tx_power_set(dBm),Rx_power_aver+pathloss(dBm),bb_tx_power_idx,ramp_on(us),ramp_off(us),tx_shr,bb_scale,tx_err,suer_dcm,mu_dcm,doppler,midamble\n');
        else:
            fid.write(
                'wifi_format, cbw, ht_dup, chan_sel, rate, data_len, short_gi,giltf, rf_chan, freq_tx, backoff(dB), cable_loss(dB)\n')
        fid.close()

        ext_atten = cable_loss
        w_str = ''
        data = []
        time_start = time.time()
        self.wifi.cmdstop()

        date_stamp = time.strftime('%Y-%m%d-%H%M%S', time.localtime())
        test_report_risc = './log/wifi_tx/risc_wifitx_%sm_%s_nss%d_stbc%d_fec_coding%d_channel%d_%s.csv' % (bss_bw, wifi_format, nsts,stbc,fec_coding , channel[0]  ,date_stamp)
        fid_risc = open(test_report_risc, 'w')
        flag_title_done = 0;
        nss_is_2 = (nsts == 2) & (stbc == 0)

        ampdu_len_para=ampdu_len<<24;


        ##########################tester body##########################
        for chan in channel:
            if chan > 6000:
                en_6g = 1
                print("I am @6G")
                # self.wifiapi.channel.req_com('chip_6g_enable 1')
                time.sleep(1);
            # else:
            #     print("I am @5G")
            #     self.wifiapi.channel.req_com('chip_6g_enable 0')
            #     en_6g = 0
            #     time.sleep(1);
            if (nss_is_2 | stbc):
                self.wifiapi.channel.req_com('chip_mode_sel 2')
                print("chip_mode_sel 2")
            else:
                self.wifiapi.channel.req_com('chip_mode_sel 1')
                print("chip_mode_sel 1")

            print("******************************PHY MODE SET***********************************")
            print((self.wifiapi.channel.req_com('phy_mode %d %d' % (phy_mode, m20_position))))
            for wifi_format in wififormat_list:
                print("wififormat_list=%s" % wififormat_list)
                test_para = self.tester_vsa_para(wifi_format, para_set);
                if self.he_giltf_check(wifi_format, giltf) == False:
                    return False
                if (wifi_format == 'hesu'):
                    # self.wifi.cmdstop()
                    time.sleep(0.01);
                    ##self.HWREG.MAC_TXQMEM.MACTXQ0_HESIG2.reg_txq0_he_ersu=0;
                    test_para = test_para + ['', '', '', '', '', '', '', '', '', ''];
                elif (wifi_format == 'heer'):
                    test_para = test_para + ['', '', '', '', '', '', '', '', '', ''];

                # if(wifi_format=='dup'):
                #     if
                #     ht_dup = 1;
                # else:
                #     ht_dup = 0;

                if False == self.cbw_check(cbw, bss_bw, wifi_format, chan_sel):  return False

                # date_stamp=time.strftime('%Y-%m%d-%H%M%S', time.localtime())
                # test_report_risc = './log/wifi_tx/risc_wifitx_%sm_%s_%s.csv' %(bss_bw, wifi_format, date_stamp)
                # fid_risc=open(test_report_risc, 'w')
                if (wifi_format == '11b'):
                    if (shortlog == 0):
                        basic_analysis_list = ['type', 'modType', 'ana_sig', 'bitRate', 'numPsduBytes', 'psduCrcFail',
                                               'longPreamble', 'phaseErr', 'freqErr', 'clockErr',
                                               'loLeakageDb', 'aver_evmAll', 'max_evmAll', 'min_evmAll', 'eva_power',
                                               'max_power', 'min_power', 'ramp_on',
                                               'ramp_off'];  # 'on_time_vect','off_time_vect'?
                        conf_title_str = 'wifi_format,cbw,ht_dup,chan_sel,rate,data_len,short_gi,giltf,heltf_num,rf_chan,freq_tx,backoff(dB),cable_loss(dB),nominal_pe,tx_power_set(dBm),bb_tx_power_idx,tx_shr,tx_err';
                    else:
                        basic_analysis_list = ['type', 'bitRate', 'numPsduBytes', 'psduCrcFail', 'longPreamble',
                                               'aver_evmAll', 'eva_power', 'ramp_on', 'ramp_off', 'loLeakageDb',
                                               'spectrumMarginOffsetFreqHz', 'spectrumMarginDb_nss1', 'spectrumMarginDb_nss2', 'amplitude_imbalace',
                                               'phase_imbalance', 'evm_margin'];  # 'on_time_vect','off_time_vect'?
                        conf_title_str = 'wifi_format,rate,data_len,rf_chan,freq_tx,tx_power_set(dBm),cable_loss(dB),tx_power_set(dBm),tx_shr,bb_scale';
                elif (wifi_format == 'nht' or wifi_format == 'dup'):
                    if (shortlog == 0):
                        basic_analysis_list = ['type', 'cbw', 'format', 'ana_sig', 'dataRate', 'numSymbols', 'N_stf',
                                               'numPsduBytes', 'fec_cod', 'mcs', 'codingRate', 'lsigCrcFail',
                                               'psduCrcFail', 'phase_error', 'freq_error', 'sys_clk_err',
                                               'LO_leakage', 'aver_evmAll', 'max_evmAll', 'min_evmAll', 'eva_power',
                                               'max_power', 'min_power', 'ramp_on', 'ramp_off'];
                        conf_title_str = 'wifi_format,cbw,ht_dup,chan_sel,rate,data_len,short_gi,giltf,heltf_num,rf_chan,freq_tx,backoff(dB),cable_loss(dB),nominal_pe,tx_power_set(dBm),bb_tx_power_idx,tx_shr,tx_err';
                    else:
                        basic_analysis_list = ['type', 'dataRate', 'numSymbols', 'numPsduBytes', 'lsigCrcFail',
                                               'psduCrcFail', 'phase_error', 'freq_error', 'sys_clk_err', 'aver_evmAll',
                                               'aver_evmDataAll', 'aver_evmPilotAll', 'eva_power', 'LO_leakage',
                                               'spectralFlatness_margin', 'spectralFlatness_otone',
                                               'spectrumMarginOffsetFreqHz', 'spectrumMarginDb_nss1', 'spectrumMarginDb_nss2', 'amplitude_imbalace',
                                               'phase_imbalance', 'evm_margin'];
                        conf_title_str = 'wifi_format,ht_dup,rate,data_len,rf_chan,freq_tx,tx_power_set(dBm),cable_loss(dB)';

                elif (wifi_format == 'ht'):
                    if (shortlog == 0):
                        basic_analysis_list = ['type', 'cbw', 'format', 'ana_sig', 'dataRate', 'numSymbols', 'N_stf',
                                               'numPsduBytes', 'fec_cod', 'mcs', 'codingRate', 'lsigCrcFail',
                                               'psduCrcFail', 'phase_error', 'freq_error', 'sys_clk_err',
                                               'LO_leakage', 'aver_evmAll', 'max_evmAll', 'min_evmAll', 'eva_power',
                                               'max_power', 'min_power', 'ramp_on', 'ramp_off'];
                        conf_title_str = 'wifi_format,cbw,ht_dup,chan_sel,rate,data_len,short_gi,giltf,heltf_num,rf_chan,freq_tx,backoff(dB),cable_loss(dB),nominal_pe,tx_power_set(dBm),bb_tx_power_idx,tx_shr,tx_err';
                    else:
                        basic_analysis_list = ['type', 'dataRate', 'numSymbols', 'numPsduBytes', 'psduCrcFail',
                                               'phase_error', 'freq_error', 'sys_clk_err', 'aver_evmAll', 'max_evmAll',
                                               'min_evmAll', 'aver_evmDataAll', 'aver_evmPilotAll', 'eva_power','fec_cod',
                                               'LO_leakage', 'spectralFlatness_margin', 'spectralFlatness_otone',
                                               'spectrumMarginOffsetFreqHz', 'spectrumMarginDb_nss1', 'spectrumMarginDb_nss2', 'amplitude_imbalace',
                                               'phase_imbalance', 'evm_margin', 'nSTS'];
                        conf_title_str = 'wifi_format,cbw,rate,data_len,rf_chan,freq_tx,short_gi,tx_power_set(dBm),cable_loss(dB),bb_tx_power_idx,tx_shr,bb_scale';
                elif (wifi_format == 'vht'):  # TODO
                    if (shortlog == 0):
                        basic_analysis_list = ['type', 'cbw', 'format', 'ana_sig', 'dataRate', 'numSymbols', 'N_stf',
                                               'numPsduBytes', 'fec_cod', 'mcs', 'codingRate', 'lsigCrcFail',
                                               'psduCrcFail', 'phase_error', 'freq_error', 'sys_clk_err',
                                               'LO_leakage', 'aver_evmAll', 'max_evmAll', 'min_evmAll', 'eva_power',
                                               'max_power', 'min_power', 'ramp_on', 'ramp_off'];
                        conf_title_str = 'wifi_format,cbw,ht_dup,chan_sel,rate,data_len,short_gi,giltf,heltf_num,rf_chan,freq_tx,backoff(dB),cable_loss(dB),nominal_pe,tx_power_set(dBm),bb_tx_power_idx,tx_shr,tx_err';
                    else:
                        basic_analysis_list = ['type', 'dataRate', 'numSymbols', 'numPsduBytes', 'psduCrcFail',
                                               'phase_error', 'freq_error', 'sys_clk_err', 'aver_evmAll', 'max_evmAll',
                                               'min_evmAll', 'aver_evmDataAll', 'aver_evmPilotAll', 'eva_power','fec_cod',
                                               'LO_leakage', 'spectralFlatness_margin', 'spectralFlatness_otone',
                                               'spectrumMarginOffsetFreqHz', 'spectrumMarginDb_nss1', 'spectrumMarginDb_nss2', 'amplitude_imbalace',
                                               'phase_imbalance', 'evm_margin', 'nSTS'];
                        conf_title_str = 'wifi_format,cbw,rate,data_len,rf_chan,freq_tx,short_gi,tx_power_set(dBm),cable_loss(dB),bb_tx_power_idx,tx_shr,bb_scale';

                elif (wifi_format == 'hesu' or wifi_format == 'heer'):
                    if (shortlog == 0):
                        basic_analysis_list = ['type', 'cbw', 'format', 'ana_sig', 'dataRate', 'numSymbols', 'N_stf',
                                               'Nuser', 'numPsduBytes', 'fec_cod', 'mcs', 'codingRate', 'lsigCrcFail',
                                               'psduCrcFail', 'sigCrcFail', 'nSTS', 'nTone',
                                               'gi', 'aFactor', 'pe', 'ldpcExtra', 'heLtf', 'dcm', 'dpl', 'mid',
                                               'phase_error', 'freq_error', 'sys_clk_err', 'ruIndex', 'ruSize', 'staID',
                                               'LO_leakage', 'aver_evmAll', 'max_evmAll', 'min_evmAll', 'eva_power',
                                               'max_power', 'min_power', 'ramp_on', 'ramp_off', 'fec_cod', 'ldpcExtra',
                                               'spectralFlatness',
                                               'spectralFlatnessHighLimit', 'spectralFlatnessLowLimit',
                                               'spectralFlatness_margin', 'spectralFlatness_otone',
                                               'spectralFlatness_per_packet', 'spectrumMarginOffsetFreqHz',
                                               'spectrumMarginDb_nss1', 'spectrumMarginDb_nss2', 'evm_margin'];
                        conf_title_str = 'wifi_format,cbw,ht_dup,chan_sel,rate,data_len,short_gi,giltf,heltf_num,rf_chan,freq_tx,backoff(dB),cable_loss(dB),nominal_pe,tx_power_set(dBm),bb_tx_power_idx,tx_shr,tx_err,spectralFlatness,spectralFlatnessHighLimit,spectralFlatnessLowLimit,spectralFlatness_margin,spectralFlatness_otone,spectralFlatness_per_packet';
                    else:
                        basic_analysis_list = ['format', 'dataRate', 'numSymbols', 'numPsduBytes', 'psduCrcFail', 'gi',
                                               'heLtf', 'phase_error', 'freq_error', 'sys_clk_err', 'aver_evmAll',
                                               'max_evmAll', 'min_evmAll', 'aver_evmDataAll', 'aver_evmPilotAll',
                                               'eva_power', 'max_power', 'min_power', 'dcm', 'aFactor', 'pe', 'fec_cod',
                                               'ldpcExtra', 'LO_leakage',
                                               'spectralFlatness_margin', 'spectralFlatness_otone',
                                               'spectrumMarginOffsetFreqHz', 'spectrumMarginDb_nss1', 'spectrumMarginDb_nss2', 'amplitude_imbalace',
                                               'phase_imbalance', 'evm_margin', 'nSTS'];
                        conf_title_str = 'wifi_format,rate,data_len,giltf,heltf_num,rf_chan,freq_tx,nominal_pe,tx_power_set(dBm),cable_loss(dB),bb_tx_power_idx,tx_shr,bb_scale,scr_seed,ldpcExtra_cfg';

                if (flag_title_done == 0):
                    xlheader_str = self.xlheader_gen(basic_analysis_list, conf_title_str, nss_is_2);
                    print("xlheader_str", xlheader_str)
                    fid_risc.write(xlheader_str)
                    fid_risc.close()
                flag_title_done = 1;

                # print("debug point 1 *******************************\n")

                for cbw_var in cbw:
                    if (wifi_format == 'dup'):
                        if cbw_var == 1:
                            ht_dup = 1;
                        elif cbw_var == 2:
                            ht_dup = 2;
                        elif cbw_var == 3:
                            ht_dup = 3;
                    else:
                        ht_dup = 0;

                    print("***************************SET IQXEL RATE******************************")

                    if phy_mode in [0, 1, 2]:
                        sample_rate = '160e6'
                    elif phy_mode == 3:
                        sample_rate = '480e6'

                    print("sample_rate = ", sample_rate)

                    ####chansel_num_list=self.chansel_num_gen_fixed(bss_bw,wifi_format,cbw_var,chan_sel)

                    # chansel_num_list = [0]



                    if bss_bw == 160:
                        bw_tmp = 3
                        chansel_num_list = [3]
                    elif bss_bw == 80:
                        bw_tmp = 2
                        chansel_num_list = [2]
                    elif bss_bw == 40:
                        bw_tmp = 1
                        chansel_num_list = [1]
                    elif bss_bw == 20:
                        bw_tmp = 0
                        chansel_num_list = [0]

                    print("***************chansel_num_list=", chansel_num_list)

                    for chansel_num in chansel_num_list:
                        if chan == 14:
                            freq = 2484
                        elif chan > 14:
                            freq = chan
                        else:
                            freq = 2412 + 5 * (chan - 1)

                        if only_check != 1:
                            res = self.wifi.cmdstop()

                            time.sleep(0.1)


                            # if (bss_bw == 160):
                            #     time.sleep(0.2)
                            #     #print((self.wifiapi.rfchsel(chan, chansel_num)))
                            #     print((self.wifiapi.rfchsel(chan, 3)))
                            #     if(nss_is_2):
                            #         self.wifiapi.channel.req_com('rf_chan_sel 1')
                            #         print((self.wifiapi.rfchsel(chan, 3)))
                            #     #time.sleep(0.2)
                            # elif (bss_bw == 80):
                            #     #print((self.wifiapi.rfchsel(chan, chansel_num)))
                            #     time.sleep(0.2)
                            #     print((self.wifiapi.rfchsel(chan, 2)))
                            #     #print((self.wifiapi.rfchsel(chan, chansel_num)))
                            #     #time.sleep(0.2)
                            # elif (bss_bw == 40):
                            #     ###self.mem.wr(0x6009f0cc, 0x1020)
                            #     #print((self.wifiapi.rfchsel(chan, chansel_num)))
                            #     time.sleep(0.2)
                            #     ###self.mem.wr(0x6009f0cc, 0x2121)
                            #     print((self.wifiapi.rfchsel(chan, 1)))
                            #     #time.sleep(0.2)
                            # elif (bss_bw == 20):
                            #     ###self.mem.wr(0x6009f0cc, 0x1020)
                            #     time.sleep(0.2)
                            #     print((self.wifi.rfchsel(chan, 0)))
                            #     #time.sleep(0.2)
                            #     ###self.mem.wr(0x6009f0cc, 0x2121)
                            #     ###print((self.wifi.rfchsel(chan, 0)))
                            #     ###time.sleep(1)
                            # else:
                            #     ###self.mem.wr(0x6009f0cc, 0x1020)
                            #     time.sleep(0.2)
                            #     print((self.wifi.rfchsel(chan, 0)))
                            #     time.sleep(0.2)
                            #     ###self.mem.wr(0x6009f0cc, 0x2121)
                            #     ###print((self.wifi.rfchsel(chan, 0)))
                            #     ###time.sleep(1)
                            fid = open(test_report, 'a')
                            fid_risc = open(test_report_risc, 'a')

                            bb_format = self.bb_format_gen(wifi_format);  ## 1:hesu,2:heer;3:hetb 3:vht
                            giltf_list = self.he_giltf_gen(wifi_format, giltf);
                            nominal_pe_list = self.he_nominal_pe_list_gen(wifi_format, nominal_pe);
                            shortgi_list = self.shortgi_list_gen(wifi_format, short_gi);
                            [dcm_on_list, dpl_on_list] = self.he_dcm_dpl_on_gen(wifi_format, dcm_on_enb, dpl_on_enb);
                            if (wifi_format == 'hetb' or wifi_format == 'hemu'):
                                print("************************WARNING****************************")
                                print("**********************!!!!!!!!!!!**************************")
                                print("txtest_normal_top function Un-support HETB and HEMU check!!")
                                print("**********************-----------**************************")
                                print("**********************-----------**************************")
                                return False;
                            else:  ##if wifi_format == 'hetb' or 'hemu'
                                ##--0301--self.txtest_reg_config(wifi_format = wifi_format,faketb_enb='disable',mac_hetb_para_list=[],mac_norm_para_list=[1]);
                                if (wifi_format == 'hesu' or wifi_format == 'heer'):
                                    print(self.wifiapi.channel.req_com('phy_11ax_tx_set 1'))
                                else:
                                    print(self.wifiapi.channel.req_com('phy_11ax_tx_set 0'))

                                print(self.wifiapi.force_txpow_enb(0))
                                num_heltf_var = num_heltf;
                                for dcm_on in dcm_on_list:
                                    for vsg_dpl_on in dpl_on_list:
                                        mid_list = self.he_mid_gen(vsg_dpl_on, mid_enb);
                                        for vsg_mid in mid_list:
                                            for giltf_num in giltf_list:
                                                for nominal_pe_var in nominal_pe_list:
                                                    # self.HWREG.MAC_SCH.MACAXOPTIONS2.reg_nominal_pkt_padding= nominal_pe_var;
                                                    for shortgi_var in shortgi_list:
                                                        print("short_gi = ", shortgi_var)
                                                        rate_list = self.rate_gen(rate_sym, bss_bw, wifi_format,
                                                                                  cbw_var, dcm_on, fec_coding, nss_is_2,
                                                                                  stbc=stbc , ru106=ru106)
                                                        print("rate_list = ", rate_list)
                                                        if rate_list == False:
                                                            return False
                                                        for rate in rate_list:
                                                            ##no need to set ?
                                                            ##self.mac_nominal_pe_set(wifi_format,rate,nominal_pe_var,nss_is_2,bss_bw);

                                                            if wifi_format == 'ht':
                                                                meas_type_list = meas_type_11n_list;
                                                                vect_type_list = vect_type_11n_list;
                                                            if wifi_format == 'vht':
                                                                meas_type_list = meas_type_11ac_list;
                                                                vect_type_list = vect_type_11ac_list;
                                                            elif (wifi_format == 'hesu' or wifi_format == 'heer'):
                                                                meas_type_list = meas_type_11ax_list;
                                                                vect_type_list = vect_type_11ax_list;
                                                            else:
                                                                if bss_bw == 10:
                                                                    test_para = test_para + ['half']
                                                                    meas_type_list = meas_type_11ag_list;
                                                                    vect_type_list = vect_type_11ag_list;
                                                                elif bss_bw == 5:
                                                                    test_para = test_para + ['quar']
                                                                    meas_type_list = meas_type_11ag_list;
                                                                    vect_type_list = vect_type_11ag_list;
                                                                else:
                                                                    if rate in ['lr_0_0.125m', 'lr_1_0.25m',
                                                                                'lr_2_0.5m', 'lr_3_0.25m', 'lr_4_0.5m',
                                                                                'lr_5_1m', 'lr_6_0.25m', 'lr_7_0.5m',
                                                                                '1m', '2ml', '2ms', '5.5ml', '5.5ms',
                                                                                '11ml', '11ms']:
                                                                        meas_type_list = meas_type_11b_list;
                                                                        vect_type_list = vect_type_11b_list;
                                                                    else:
                                                                        meas_type_list = meas_type_11ag_list;
                                                                        vect_type_list = vect_type_11ag_list;
                                                            test_para = test_para + [alys_offs] + [
                                                                cap_num];  ##add packet offset and analysis packet nuber
                                                            ## TBD: to fix the scramble seed here
                                                            print("!!!debug flg scr_seed", scr_seed_lst[0])
                                                            if scr_seed_lst[0] == 'random':
                                                                ###self.HWREG.BB_TX.BBTXCONF.reg_seed_load = 1;
                                                                scr_seed_list = [random.randint(1, 127), ];
                                                            elif scr_seed_lst[0] == 'fix':
                                                                ###self.HWREG.BB_TX.BBTXCONF.reg_seed_load = 1;
                                                                scr_seed_list = scr_seed_lst[1];
                                                            elif scr_seed_lst[0] == 'default':
                                                                ###self.HWREG.BB_TX.BBTXCONF.reg_seed_load = 0;
                                                                ###seed_default = self.HWREG.BB_TX.BBTXCONF.reg_seed;
                                                                ###scr_seed_list = [seed_default];
                                                                scr_seed_list = [0];
                                                            else:
                                                                ###self.HWREG.BB_TX.BBTXCONF.reg_seed_load = 0;
                                                                ###seed_default = self.HWREG.BB_TX.BBTXCONF.reg_seed;
                                                                scr_seed_list = [0];
                                                            for scr_seed in scr_seed_list:
                                                                print("!!!debug flg 1")
                                                                # self.HWREG.BB_TX.BBTXCONF.reg_seed = scr_seed;
                                                                [power_index_list,
                                                                 powr_real] = self.non_hetb_power_table(pwr_chk_enb,
                                                                                                        wifi_format,
                                                                                                        rate,
                                                                                                        tx_power_fix,
                                                                                                        tx_shr);
                                                                print("!!!debug flg 2")
                                                                for pi in range(0, len(power_index_list)):
                                                                    # power_index_var_tmp = powr_real[pi];
                                                                    power_index_var = powr_real[pi];
                                                                    # power_index_reg = power_index_list[pi];
                                                                    print("!!!debug: the power_index_var is %d " % (
                                                                        int(power_index_var)))

                                                                    # self.HWREG.MAC_TXQMEM.MACTXQ0_TXPWR.reg_txq0_tx_pwr_20m = 5
                                                                    # print("!!!The reg_txq0_tx_pwr_20m is:",self.HWREG.MAC_TXQMEM.MACTXQ0_TXPWR.reg_txq0_tx_pwr_20m)
                                                                    print("!!!The cbw_var is:", cbw_var)
                                                                    ###if(cbw_var==1):
                                                                    ###self.HWREG.MAC_TXQMEM.MACTXQ0_TXPWR.reg_txq0_tx_pwr_40m= int(power_index_var);
                                                                    ###elif(cbw_var==0):
                                                                    ###self.HWREG.MAC_TXQMEM.MACTXQ0_TXPWR.reg_txq0_tx_pwr_20m= int(power_index_var);
                                                                    ###self.HWREG.MAC_TXQMEM.MACTXQ0_TXPWR.reg_txq0_tx_pwr_40m = int(power_index_var)
                                                                    # print("!!!The reg_txq0_tx_pwr_20m is:",self.HWREG.MAC_TXQMEM.MACTXQ0_TXPWR.reg_txq0_tx_pwr_20m)
                                                                    ###else:
                                                                    ###self.HWREG.MAC_TXQMEM.MACTXQ0_TXPWR.reg_txq0_tx_pwr_20m= int(power_index_var);
                                                                    ## for c6 FMC temp
                                                                    ##                                                                    reg_tmp = 0xa59e0000 + (-10-power_index_var)*65536;
                                                                    ##                                                                    print("debug: the cfg reg_tmp for pwr is %s" %reg_tmp)
                                                                    ##                                                                    self.wifiapi.slv_wr("0x60006000",reg_tmp)
                                                                    if bb_format >= 1 :
                                                                        if bss_bw == 20 :
                                                                            power_index_var_offset = power_index_var 
                                                                        elif bss_bw == 40 :
                                                                            power_index_var_offset = power_index_var + 1
                                                                        elif bss_bw == 80 :
                                                                            power_index_var_offset = power_index_var + 3
                                                                        elif bss_bw == 160 :
                                                                            power_index_var_offset = power_index_var + 5
                                                                    else :
                                                                        power_index_var_offset = power_index_var 

                                                                    power_backoff = round((20 - power_index_var_offset) * 4);
                                                                    print(
                                                                        "************************power_index_var is %d**********************" % (
                                                                            power_index_var));
                                                                    print("************************power_backoff is %d**********************" % (power_backoff));
                                                                    if power_backoff < 0:
                                                                        power_backoff = 256 + power_backoff;

                                                                    time.sleep(0.1);


                                                                    print("***************************SET CHANNEL******************************")

                                                                    self.wifiapi.channel.req_com('rf_chan_sel 0')
                                                                    time.sleep(0.1)

                                                                    print((self.wifiapi.rfchsel(chan, bw_tmp)))
                                                                    self.wifiapi.channel.req_com('target_power_backoff %d' % (power_backoff))

                                                                    print("*************is nss%d  stbc%d"%(nsts,stbc))
                                                                    time.sleep(0.1)
                                                                    if (ant_sel==3):
                                                                        self.wifiapi.channel.req_com('rf_chan_sel 1')
                                                                        time.sleep(0.1)
                                                                        # if chan > 6000:
                                                                        #     en_6g = 1
                                                                        #     print("I am @6G")
                                                                        #     self.wifiapi.channel.req_com(
                                                                        #         'chip_6g_enable 1')
                                                                        #     time.sleep(1);
                                                                        # else:
                                                                        #     print("I am @5G")
                                                                        #     self.wifiapi.channel.req_com(
                                                                        #         'chip_6g_enable 0')
                                                                        #     en_6g = 0
                                                                        #     time.sleep(1);
                                                                        print((self.wifiapi.rfchsel(chan, bw_tmp)))
                                                                        self.wifiapi.channel.req_com('target_power_backoff %d' % (power_backoff))






                                                                    time.sleep(0.1);

                                                                    bb_scale_list = self.bb_scale_gen(bb_scale_enb);
                                                                    for bb_scale in bb_scale_list:
                                                                        ###if(bb_scale_enb==1):
                                                                        ###    res = self.wifi.cmdstop();
                                                                        ###    time.sleep(0.01);
                                                                        ###    self.HWREG.BB_TX.BBTX_CFO.reg_tx_bb_scale_db=bb_scale;
                                                                        ###else:
                                                                        ###    pass;
                                                                        ##print ("bb_scale %s",bb_scale);
                                                                        pwr_chage = power_index_var + round(
                                                                            bb_scale * 0.25, 0)

                                                                        # [max_pwr,vsa_trig_pow_lev] = self.vsa_pwr_para_gen(pathloss=ext_atten,wifi_format=wifi_format,faketb_enb='disable',pwr_chk_enb=pwr_chk_enb,pwr_idx=power_index_var,tx_shr=tx_shr,trig_rssi=0);
                                                                        # ref to the rtl, pwr value set sat -->20-(-11)='b011111
                                                                        if (pwr_chage < -12):
                                                                            pwr_chage = -12;
                                                                            print(
                                                                                "Warning: Due to min Power saturation, the pwr_chage %s",
                                                                                pwr_chage);
                                                                        elif (pwr_chage > 21):
                                                                            pwr_chage = 21;
                                                                            print(
                                                                                "Warning: Due to max Power saturation, the pwr_chage %s",
                                                                                pwr_chage);

                                                                        print(
                                                                            "************************** the pwr_chage = %d"%
                                                                            pwr_chage);

                                                                        if (pathloss_comp_on == 1):
                                                                            pathloss = 0;
                                                                        else:
                                                                            pathloss = ext_atten;
                                                                        [max_pwr,
                                                                         vsa_trig_pow_lev] = self.vsa_pwr_para_gen(
                                                                            pathloss=pathloss, wifi_format=wifi_format,
                                                                            faketb_enb='disable',
                                                                            pwr_chk_enb=pwr_chk_enb, pwr_idx=pwr_chage,
                                                                            tx_shr=tx_shr, trig_rssi=0,
                                                                            pathloss_comp_on=pathloss_comp_on);
                                                                        print(
                                                                            "!!!!debug: pwr change is %s and tester ref power is %s" % (
                                                                            pwr_chage, max_pwr));
                                                                        print(
                                                                            "self.datalen_check(data_len_in:%s, wifi_format:%s, rate:%s, run_mode:%s, data_len_regr_list:%s, vsg_dpl_on:%s, vsg_mid:%s, dcm_on:%s,afactor_scan:%s,target_afactor:%s)" % (
                                                                            data_len_in, wifi_format, rate, run_mode,
                                                                            data_len_regr_list, vsg_dpl_on, vsg_mid,
                                                                            dcm_on, afactor_scan, target_afactor));
                                                                        datalen_list = self.datalen_check(data_len_in,
                                                                                                          wifi_format,
                                                                                                          242, rate,
                                                                                                          run_mode,
                                                                                                          data_len_regr_list,
                                                                                                          vsg_dpl_on,
                                                                                                          vsg_mid,
                                                                                                          dcm_on,
                                                                                                          afactor_scan,
                                                                                                          target_afactor);
                                                                        print("the datalen_list is %s" % datalen_list);
                                                                        for data_len in datalen_list:
                                                                            SampleTime_us = (2 ** mode_11p) * (
                                                                                        cap_num + alys_offs) * (
                                                                                                        math.ceil(
                                                                                                            self.SampleTime_Gen(
                                                                                                                bss_bw,
                                                                                                                cbw_var,
                                                                                                                wifi_format,
                                                                                                                rate,
                                                                                                                shortgi_var,
                                                                                                                data_len,
                                                                                                                giltf_num,
                                                                                                                1,
                                                                                                                dcm_on,
                                                                                                                vsg_dpl_on,
                                                                                                                vsg_mid)) + 16 + frm_delay) + 1000;
                                                                            SampleTime_us = 150000
                                                                            print("SampleTime_us = %d \n",
                                                                                  SampleTime_us)
                                                                            print("***********************************wifi_format:%s bw:%d rate:%s****************"%(wifi_format,cbw_var,rate))
                                                                            (hesiga1, hesiga2,
                                                                             ldpcExtra_cfg) = self.hesiga_gen(
                                                                                wifi_format, rate, cbw_var, giltf_num,
                                                                                dcm_on, vsg_dpl_on, vsg_mid, data_len,
                                                                                fec_coding, nsts, stbc, is_hesu_ru106)
                                                                            print("**********************************hesiga1/2:%d %d ****************"%(hesiga1,hesiga2))

                                                                            (vhtsig1, vhtsig2) = self.vhtsig_gen(
                                                                                stbc=stbc, rate=rate, cbw=cbw_var,
                                                                                shortgi=shortgi_var, data_len=data_len,
                                                                                nsts=nsts, fec_coding=fec_coding)
                                                                            print("************************************vhtsig1/2:%d %d ****************"%(vhtsig1,vhtsig2))
                                                                            if (wifi_format == 'vht'):
                                                                                sig1 = vhtsig1;
                                                                                sig2 = vhtsig2;
                                                                            else:
                                                                                sig1 = hesiga1;
                                                                                sig2 = hesiga2;

                                                                            print("debug point 4 ***************after sig1 sig2  gen****************")

                                                                            u0 = time.time()
                                                                            
                                                                            if bb_format == 1 | bb_format == 2 :
                                                                                gi_esp = giltf_num
                                                                            else :
                                                                                gi_esp = short_gi

                                                                            nsts_esp = nsts -1 
                                                                            for i in range(0, loop_num):
                                                                                if wifi_format == 'ht' :
                                                                                    self.wifi.tx_esp_test(rate, 0, ampdu_len_para,data_len,
                                                                                                 cbw_var, ht_dup,
                                                                                                 shortgi_var,
                                                                                                 backoff_qdb, frm_delay,
                                                                                                 dis_cca, bb_format,
                                                                                                 sig1, sig2, ant_sel ,fec_coding , bss_bw ,gi_esp ,nsts_esp ,freq ,power_backoff)
                                                                                                                                                                    
                                                                                    print(
                                                                                        "self.wifi.tx_esp_test(rate:%s, 0, ampdu_len:0x%x, data_len:%s, cbw_var:%s, ht_dup:%s, shortgi_var:%s, backoff_qdb:%s, frm_delay:%s, dis_cca:%s,bb_format:%s,sig1:%s,sig2:%s,ant_sel:%s ,fec_coding:%s ,bss_bw:%s ,gi_esp:%s ,nsts_esp:%s,freq:%s ,backoff:%s)" % (
                                                                                        rate,ampdu_len, data_len, cbw_var, ht_dup,
                                                                                        shortgi_var, backoff_qdb,
                                                                                        frm_delay,
                                                                                        dis_cca, bb_format, sig1, sig2,
                                                                                        ant_sel ,fec_coding ,bss_bw ,gi_esp ,nsts_esp,freq ,power_backoff));
                                                                                    print(
                                                                                        "self.wifi.tx_esp_test('%s',0,0x%x,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)" % (
                                                                                            rate, ampdu_len,data_len, cbw_var, ht_dup,
                                                                                            shortgi_var, backoff_qdb, frm_delay,
                                                                                            dis_cca, bb_format, sig1, sig2,
                                                                                            ant_sel ,fec_coding,bss_bw ,gi_esp ,nsts_esp,freq ,power_backoff));
                                                                                else :                                                                                    
                                                                                    self.wifi.txtest(rate, 0, ampdu_len_para,data_len,
                                                                                                     cbw_var, ht_dup,
                                                                                                     shortgi_var,
                                                                                                     backoff_qdb, frm_delay,
                                                                                                     dis_cca, bb_format,
                                                                                                     sig1, sig2, ant_sel ,fec_coding , bss_bw ,gi_esp ,nsts_esp)
                                                                                    # print("debug point 5***************after TX txtest****************")
                                                                                    print(
                                                                                        "self.wifi.txtest(rate:%s, 0, ampdu_len:0x%x, data_len:%s, cbw_var:%s, ht_dup:%s, shortgi_var:%s, backoff_qdb:%s, frm_delay:%s, dis_cca:%s,bb_format:%s,sig1:%s,sig2:%s,ant_sel:%s ,fec_coding:%s ,bss_bw:%s ,gi_esp:%s ,nsts_esp:%s)" % (
                                                                                            rate,ampdu_len, data_len, cbw_var, ht_dup,
                                                                                            shortgi_var, backoff_qdb,
                                                                                            frm_delay,
                                                                                            dis_cca, bb_format, sig1, sig2,
                                                                                            ant_sel ,fec_coding ,bss_bw ,gi_esp ,nsts_esp));
                                                                                    print(
                                                                                        "self.wifi.txtest('%s',0,0x%x,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)" % (
                                                                                            rate, ampdu_len,data_len, cbw_var, ht_dup,
                                                                                            shortgi_var, backoff_qdb, frm_delay,
                                                                                            dis_cca, bb_format, sig1, sig2,
                                                                                            ant_sel ,fec_coding,bss_bw ,gi_esp ,nsts_esp));
                                                                                    cmdstr_print = "test_top.wifi.txtest('%s',0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) \n" % (
                                                                                            rate, data_len, cbw_var, ht_dup,
                                                                                            shortgi_var, backoff_qdb, frm_delay,
                                                                                            dis_cca, bb_format, sig1, sig2,
                                                                                            ant_sel,fec_coding,bss_bw ,gi_esp ,nsts_esp)
                                                                                    with open(
                                                                                            'D:/chip_test/dev/chip_tx/eagletest/py_script_rls3p0_chip/tx_cmd_list.txt',
                                                                                            'a', encoding='utf-8') as file:
                                                                                        file.write(cmdstr_print)
                                                                                        file.write("\n")

                                                                                if (pathloss_comp_on == 0):
                                                                                    path_loss = 0;
                                                                                else:
                                                                                    path_loss = cable_loss;

                                                                                tester_inst = tester.tester(
                                                                                    rf_freqMhz=freq, pwr=max_pwr,
                                                                                    data_rate=rate, testpara=test_para,
                                                                                    unit_no=vsa_port, mode='measure',
                                                                                    auto_range=0,
                                                                                    dut_format=wifi_format,
                                                                                    SampleTime_us=SampleTime_us,
                                                                                    path_loss=path_loss,
                                                                                    mimo_siso_mode=mimo_siso_mode,
                                                                                    ant_sel=ant_sel,
                                                                                    sample_rate=sample_rate);
                                                                                if (wifi_format == 'ht'):
                                                                                    iq_mode = '11n_20';
                                                                                elif (wifi_format == 'vht'):
                                                                                    iq_mode = '11ac';
                                                                                elif (wifi_format == 'nht'):
                                                                                    iq_mode = '11a';
                                                                                elif (wifi_format == '11b'):
                                                                                    iq_mode = '11b';
                                                                                else:
                                                                                    iq_mode = '11ax';
                                                                                u0 = time.time()
                                                                                wifi_instrum.scpi_analysis_diff_format(
                                                                                    tester_inst, 1, SampleTime_us,
                                                                                    wifi_format, basic_analysis_list,
                                                                                    nss_is_2)
                                                                                self.scpi_iqv_risc = rfglobal.scpi_iqv_risc
                                                                                self.refresh_scpi_result_risc(
                                                                                    self.scpi_iqv_risc,
                                                                                    basic_analysis_list);

                                                                                # wifi_instrum.scpi_analysis(tester_inst,1,SampleTime_us,wifi_format)
                                                                                # self.scpi_iqv = rfglobal.scpi_iqv
                                                                                # self.refresh_scpi_result(self.scpi_iqv);
                                                                                ##for meas_type in meas_type_list:
                                                                                ##    res = tester_inst.getmeas(iq_mode,meas_type);
                                                                                ##    print ("iq_mode:%s    meas_type:%s   res:%s" %(iq_mode,meas_type,res));
                                                                                ##for vect_type in vect_type_list:
                                                                                ##    res = tester_inst.getvect(iq_mode,vect_type);
                                                                                ##    print ("iq_mode:%s    vect_type:%s   res:%s" %(iq_mode,vect_type,res));

                                                                                if (cmd_stop == "cmd_stop"):
                                                                                    res = self.wifi.cmdstop()
                                                                                    time.sleep(0.05);

                                                                                time.sleep(0.01);
                                                                                # reg_tx_cfo_adjust_value=self.HWREG.BB_TX.BBTX_CFO_1.reg_tx_cfo_adjust_value;
                                                                                ##reg_tx_cfo_adjust_value=0;
                                                                                time.sleep(0.01);
                                                                                ###tx_err_reg = self.HWREG.MAC_TXQMEM.MACTXQ0PMD.txq0complete_state;
                                                                                ##tx_err_reg = 0;
                                                                                ##print("xxxxxx00000000",tx_err_reg)
                                                                                ##print("reg_tx_cfo_adjust_value(txtest non-fake tb):",reg_tx_cfo_adjust_value);
                                                                                ##reg_tx_power_idx=self.HWREG.BB_TX.BBTX_CFO_3.reg_tx_power_idx;
                                                                                reg_tx_power_idx = 100;
                                                                                ###print("wifi_tx_test -> txtest_normal_top reg_tx_power_idx:",reg_tx_power_idx);
                                                                                ###print("wifi_tx_test -> txtest_normal_top tx_err_reg:",tx_err_reg);

                                                                                # w_str = '%s'%wifi_format+','+'%d'%cbw_var+','+'%d'%ht_dup+','+'%d'%+chansel_num+','+'%s'%rate+','+'%d'%data_len+','+'%d'%shortgi_var+','+'%d'%giltf_num+','+'%d'%num_heltf_var+','+'%d'%chan+','+'%d'%freq+','+'%2.2f'%(backoff_qdb/4.0)+','+'%2.1f'%ext_atten+','+'%d'%nominal_pe_var+','+'%s'%self.packet_spec+','+'%s'%self.packet_cbw+','+'%s'%self.packet_format+','+'%s'%self.packet_ana_sig+','+'%s'%self.packet_Nuser+','+'%s'%self.packet_Ntone+','+'%s'%self.packet_ru_index+','+'%s'%self.packet_ru_size+','+'%s'%self.packet_Nsts+','+'%s'%self.packet_afactor+','+'%s'%self.packet_shortgi+','+'%s'%self.packet_gi+','+'%s'%self.packet_pe+','+'%s'%self.packet_Nsym+','+'%s'%self.packet_fec_coding+','+'%s'%self.packet_mcs+','+'%s'%self.packet_coding_rate+','+'%s'%self.packet_data_rate+','+'%s'%self.packet_l_sig_crc+','+'%s'%self.packet_N_stf+','+'%s'%self.packet_he_ltf+','+'%s'%self.packet_sig_crc+','+'%s'%self.packet_psdu_length+','+'%s'%self.packet_psdu_crc+','+'%s'%self.packet_plcp_crc+','+'%s'%self.packet_sta_id+','+'%s'%self.packet_preamble_type+','+'%s'%self.packet_phase_error+','+'%s'%self.packet_freq_error+','+'%s'%self.packet_sys_clk_error+','+'%s'%self.packet_LO_leakage+','+'%s'%self.packet_evm+','+'%s'%self.packet_evm_max+','+'%s'%self.packet_evm_min+','+'%s'%self.packet_power+','+'%s'%self.packet_power_max+','+'%s'%self.packet_power_min+','+'%s'%(power_index_var)+','+'%s'%(self.packet_power )+','+'%s'%reg_tx_power_idx+','+'%s'%self.packet_ramp_on+','+'%s'%self.packet_ramp_off+','+'%d'%tx_shr+','+'%d'%bb_scale+','+'%s'%tx_err_reg+','+'%s'%self.packet_suer_dcm+','+'%s'%self.packet_mu_dcm+','+'%s'%self.packet_dpl+','+'%s'%self.packet_mid+','+'\n';
                                                                                # fid.write(w_str)
                                                                                ###tx_freq_rf  = self.HWREG.BB_TX.BBTX_CFO_2.reg_freq_rf;
                                                                                ###tx_phi_mode = self.HWREG.BB_TX.BBTX_CFO_2.reg_tx_phi_mode;
                                                                                ###tx_freq_dig = self.HWREG.BB_TX.BBTX_CFO_3.reg_freq_dig;
                                                                                ###tx_sco_mu   = self.HWREG.BB_TX.BBTX_CFO_4.reg_tx_sco_mu_coff;
                                                                                ###rx_freq_rf  = self.HWREG.BB.BB_FREQ_RF1.reg_freq_rf;
                                                                                ###rx_phi_mode = self.HWREG.BB.BB_FREQ_RF2.reg_rx_phi_mode;
                                                                                ###rx_sco_mu   = self.HWREG.BB.BB_FREQ_RF2.reg_sco_mu_coff;
                                                                                ###reg_sco_list = [str(tx_freq_rf),str(tx_phi_mode),str(tx_freq_dig),str(tx_sco_mu),str(rx_freq_rf),str(rx_phi_mode),str(rx_sco_mu)];

                                                                                if (shortlog == 0):
                                                                                    conf_data_str = '%s' % wifi_format + ',' + '%d' % cbw_var + ',' + '%d' % ht_dup + ',' + '%d' % +chansel_num + ',' + '%s' % rate + ',' + '%d' % data_len + ',' + '%d' % shortgi_var + ',' + '%d' % giltf_num + ',' + '%d' % num_heltf_var + ',' + '%d' % chan + ',' + '%d' % freq + ',' + '%2.2f' % (
                                                                                            backoff_qdb / 4.0) + ',' + '%2.1f' % ext_atten + ',' + '%d' % nominal_pe_var + ',' + '%s' % power_index_var + ',' + '%s' % reg_tx_power_idx + ',' + '%d' % tx_shr + ',' + '%s' % tx_err_reg;
                                                                                else:
                                                                                    if (wifi_format == '11b'):
                                                                                        conf_data_str = '%s' % wifi_format + ',' + '%s' % rate + ',' + '%d' % data_len + ',' + '%d' % chan + ',' + '%d' % freq + ',' + '%s' % power_index_var + ',' + '%2.1f' % ext_atten + ',' + '%s' % reg_tx_power_idx + ',' + '%d' % tx_shr + ',' + '%d' % bb_scale;
                                                                                    elif (
                                                                                            wifi_format == 'nht' or wifi_format == 'dup'):
                                                                                        # conf_data_str = '%s'%wifi_format+','+'%d'%ht_dup+','+'%s'%rate+','+'%d'%data_len+','+'%d'%chan+','+'%d'%freq+','+'%s'%power_index_var+','+'%2.1f'%ext_atten+','+'%s'%reg_tx_power_idx+','+'%d'%tx_shr+','+'%d'%bb_scale+str(tx_freq_rf)+","+str(tx_phi_mode)+","+str(tx_freq_dig)+","+str(tx_sco_mu)+","+str(rx_freq_rf)+","+str(rx_phi_mode)+","+str(rx_sco_mu);
                                                                                        conf_data_str = '%s' % wifi_format + ',' + '%d' % ht_dup + ',' + '%s' % rate + ',' + '%d' % data_len + ',' + '%d' % chan + ',' + '%d' % freq + ',' + '%s' % power_index_var + ',' + '%2.1f' % ext_atten;
                                                                                        print(
                                                                                            'debug flag0 conf_data_str=%s' % (
                                                                                                conf_data_str));
                                                                                    elif (wifi_format == 'ht'):
                                                                                        conf_data_str = '%s' % wifi_format + ',' + '%d' % cbw_var + ',' + '%s' % rate + ',' + '%d' % data_len + ',' + '%d' % chan + ',' + '%d' % freq + ',' + '%d' % shortgi_var + ',' + '%s' % power_index_var + ',' + '%2.1f' % ext_atten + ',' + '%s' % reg_tx_power_idx + ',' + '%d' % tx_shr + ',' + '%d' % bb_scale;
                                                                                    elif (wifi_format == 'vht'):
                                                                                        conf_data_str = '%s' % wifi_format + ',' + '%d' % cbw_var + ',' + '%s' % rate + ',' + '%d' % data_len + ',' + '%d' % chan + ',' + '%d' % freq + ',' + '%d' % shortgi_var + ',' + '%s' % power_index_var + ',' + '%2.1f' % ext_atten + ',' + '%s' % reg_tx_power_idx + ',' + '%d' % tx_shr + ',' + '%d' % bb_scale;
                                                                                    elif (
                                                                                            wifi_format == 'hesu' or wifi_format == 'heer'):
                                                                                        conf_data_str = '%s' % wifi_format + ',' + '%s' % rate + ',' + '%d' % data_len + ',' + '%d' % giltf_num + ',' + '%d' % num_heltf_var + ',' + '%d' % chan + ',' + '%d' % freq + ',' + '%d' % nominal_pe_var + ',' + '%s' % power_index_var + ',' + '%2.1f' % ext_atten + ',' + '%s' % reg_tx_power_idx + ',' + '%d' % tx_shr + ',' + '%d' % bb_scale + ',' + '%d' % scr_seed + ',' + '%d' % ldpcExtra_cfg;
                                                                                xldata_str = self.xldata_gen(
                                                                                    basic_analysis_list, conf_data_str,
                                                                                    nss_is_2)
                                                                                print("xldata_str", xldata_str)
                                                                                fid_risc.write(xldata_str)
                                                                                if (cmd_stop == "cmd_stop"):
                                                                                    res = self.wifi.cmdstop()
                                                                            ## for loop num
                                                                    ## for data_len
                                                                ## scramble seed
                                                        ##for rate DUT MCS
                                                    ##for short gi
                                                ##for nominal pe
                                            ##for giltf
                                        ##for midamble
                                    ##for doppler
                                ##for dcm
                            fid_risc.close()
                            # self.IQimbalanceCal(test_report_risc)
                            ##if wifi_format == 'hetb'
                        ## if only check
                        else:  ## if only check
                            """
                            if only_check != 1:
                                fid.write(w_str)
                            w_str = '%s'%wifi_format+','+'%d'%cbw_var+','+'%d'%ht_dup+','+'%d'%+chansel_num+','+'%s'%rate+','+'%d'%data_len+','+'%d'%shortgi_var+','+'%d'%chan+','+'%d'%freq+','+'%2.2f'%(backoff_qdb/4.0)+'\n';
                        fid.close()
                        """
                        ## if only check
                    ##for chansel_num
                ## for cbw_var
            ## for wifi format
        ## chan
        if (only_check != 1) & (verbose == 1):
            print('\n\n-----RFTX Test Result-----\n')
            for item in data:
                print(item)
                print('\n\n--------------------------\n')

        time_end = time.time()
        run_time = time_end - time_start
        print("Running time is: %s seconds" % run_time)

    ## def txtest ------------------------------
    #########################################################################
