import pandas as pd
import matplotlib.pyplot as plt
import os
import openpyxl
from matplotlib.pyplot import MultipleLocator
from matplotlib.backends.backend_pdf import PdfPages
import glob
import math
import datetime
import time

#testcase_list = ['11b','11g','11n','11ac','11ax']
# filename = os.listdir(r'D:/workspace/fpga/Rx_data/' + testcase)
# filename.sorted
# foldername = 'D:/workspace/fpga/Rx_data_temp_test/'
foldername = r'D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\2G\phymd20\20m\ldpc\he\wifi_txrx_test_RXSens_hesu_giltf1_phymd20_2.4G/'
# foldername = 'D:/workspace/fpga/Rx_data_compare/'
# foldername = 'D:/workspace/fpga/Rx_data/violate/'
sens_accuracy = 100
PAK_NUM = 1000
current_time = time.localtime()
sens_path = foldername+'sens_'+str(current_time.tm_year)+str(current_time.tm_mon)+str(current_time.tm_mday)+'_'+ \
            str(current_time.tm_hour)+str(current_time.tm_min)+str(current_time.tm_sec)+'.xlsx'
print(f"path:{sens_path}")
mybook=openpyxl.Workbook()
mybook.save(sens_path)
writer = pd.ExcelWriter(sens_path,mode='a',engine="openpyxl")
# subfolder_list = os.listdir(foldername)
# subfolder_list = os.scandir(foldername)
subfolder_list = next(os.walk(foldername))[1]
for subfolder_name in subfolder_list:
    pp = PdfPages(foldername + subfolder_name + '_sensitivity.pdf')
    testcase_list = os.listdir(foldername + subfolder_name + '/')
    # # 将testcase_list按照字符串中的数字排序
    # testcase_list.sort(key=lambda x: int(x.split('_')[0]))
    for testcase in testcase_list:
        testpath = foldername + subfolder_name + '/' + testcase
        os.chdir(testpath)
        my_files = sorted(glob.glob('*.csv'), key=os.path.getmtime)
        df = pd.DataFrame()
        pak_num = PAK_NUM
        for i in range(len(my_files)):
            df = df.append(pd.read_csv(testpath + '/' + my_files[i], index_col=False))
        if 'acr' in testcase or 'ACI' in testcase:
            # chan_list = df[' rx_chan_loc'].unique()
            chan_list = df[' rx_chan'].unique()
        else:
            chan_list = df[' rx_chan'].unique()
        for chan in chan_list:
            legend_convert = []
            column_convert = []
            x1 = plt.figure(dpi=64, figsize=(11,18))
            if 'acr' in testcase or 'ACI' in testcase:
                # df_chan = df[df[' rx_chan_loc'] == chan]
                # df_chan['per'] = df_chan[' DesirePackNum'].map(lambda x: 1 - min(x, pak_num) / pak_num)
                df_chan = df[df[' rx_chan'] == chan]
                df_chan['per'] = df_chan[' rxnum'].map(lambda x: 1 - min(x, pak_num) / pak_num)
            else:
                df_chan = df[df[' rx_chan'] == chan]
                df_chan['per'] = df_chan[' rxnum'].map(lambda x: 1 - min(x, pak_num) / pak_num)
            if 'acr' in testcase or 'ACI' in testcase:
                table = pd.pivot_table(df_chan, index=[" acr"], columns=["rate"], values=["per"])
                # table = pd.pivot_table(df_chan, index=[" acr"], columns=["cur_rate"], values=["per"])
            else:
                table = pd.pivot_table(df_chan, index=[" rfpwr"], columns=["rate"], values=["per"])
            if ' evm0' in df_chan.columns:
                if 'acr' in testcase or 'ACI' in testcase:
                    table_evm = pd.pivot_table(df_chan, index=[" acr"], columns=["rate"], values=[" evm0"])
                    # table_evm = pd.pivot_table(df_chan, index=[" acr"], columns=["cur_rate"], values=[" evm0"])
                else:
                    table_evm = pd.pivot_table(df_chan, index=[" rfpwr"], columns=["rate"], values=[" evm0"])
            else:
                table_evm = pd.DataFrame()

            columnlist = table.columns
            for column in columnlist:
                column_convert.append(column[1])
            table.columns = column_convert
            if not table_evm.empty:
                table_evm.columns = column_convert
            # cal sensitivity
            sens_result = list()
            for column in column_convert:
                per4pow = table[column]
                per = per4pow.values
                pow = per4pow.index

                for i in range(0,len(per)):
                    if '11b' in testcase:
                        if 'acr' in testcase or 'ACI' in testcase:
                            if per[i] > 0.08:
                                print("Case is ",testcase,i)
                                if per[i-1] == 0:
                                    delta_per = (math.log10(per[i]) - 0.0001) / sens_accuracy
                                else:
                                    delta_per = (math.log10(per[i]) - math.log10(per[i-1]))/sens_accuracy
                                per_sens = math.log10(per[i])
                                pow_sens = pow[i]
                                for j in range(0,sens_accuracy):
                                    per_sens = per_sens - delta_per
                                    pow_sens = pow_sens - 1/sens_accuracy
                                    if per_sens <= -1.096:
                                        pow_sens_result = pow_sens
                                        break
                                break
                        else:
                            # print("Case is ", testcase, i)
                            pow_sens_result = 0
                            if per[i] < 0.08:
                                if per[i] == 0:
                                    delta_per = (math.log10(per[i - 1]) + 10) / sens_accuracy
                                    per_sens = -10
                                else:
                                    delta_per = (math.log10(per[i-1]) - math.log10(per[i]))/sens_accuracy
                                    per_sens = math.log10(per[i])
                                pow_sens = pow[i]
                                pow_sens_result = 0#init
                                for j in range(0,sens_accuracy):
                                    per_sens = per_sens + delta_per
                                    pow_sens = pow_sens - 1/sens_accuracy
                                    if per_sens >= -1.096:
                                        pow_sens_result = pow_sens
                                        break
                                break
                    else:
                        if 'acr' in testcase or 'ACI' in testcase:
                            if per[i] > 0.1:
                                print("Case is ",testcase,i)
                                if per[i-1] == 0:
                                    delta_per = (math.log10(per[i]) + 2) / sens_accuracy
                                else:
                                    delta_per = (math.log10(per[i]) - math.log10(per[i-1]))/sens_accuracy
                                per_sens = math.log10(per[i])
                                pow_sens = pow[i]
                                for j in range(0,sens_accuracy):
                                    per_sens = per_sens - delta_per
                                    # print(per_sens)
                                    pow_sens = pow_sens - 1/sens_accuracy
                                    if per_sens <= -1:
                                        pow_sens_result = pow_sens
                                        break
                                break
                        else:
                            pow_sens_result = 0
                            if per[i] < 0.1:
                                print("Case is ",testcase,i)
                                if per[i] == 0:
                                    if per[i - 1] == 0:
                                        delta_per = 0
                                    else:
                                        delta_per = (math.log10(per[i - 1]) + 10) / sens_accuracy
                                    per_sens = -10
                                else:
                                    delta_per = (math.log10(per[i-1]) - math.log10(per[i]))/sens_accuracy
                                    per_sens = math.log10(per[i])
                                pow_sens = pow[i]
                                for j in range(0,sens_accuracy):
                                    per_sens = per_sens + delta_per
                                    pow_sens = pow_sens - 1/sens_accuracy
                                    if per_sens >= -1: #log
                                        pow_sens_result = pow_sens
                                        break
                                break
                sens_result.append(round(pow_sens_result,2))
            sens_dictionary = dict(zip(column_convert, sens_result))
            sens_df = pd.DataFrame(sens_dictionary,index=[0])
            # sens_df.to_csv('../sens_' + testcase + ' '+subfolder_name + ' '+'chan'+str(chan) + ' sensitivity' + '.csv', index=False)
            sens_df.to_excel(writer,sheet_name=testcase + ' '+subfolder_name + ' '+'chan'+str(chan), index=False)

            legendList = df_chan['rate'].unique()
            # legendList = df_chan['cur_rate'].unique()
            table = table[legendList]
            legend_convert = legendList
            # if testcase != '11ax':
            #     legendList = df_chan['rate'].unique()
            #     table = table[legendList]
            # else:
            #     legendList = column_convert.unique()
            #
            # for legend in legendList:
            #     legend_convert.append(legend.split('_')[0])
            custom_colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#800000', '#008000',
                             '#000080', '#808000', '#F08080', '#8080F0','#806F86','#006066']
            plt.subplot(2, 1, 1)
            for i in range(len(table.columns)):
                plt.semilogy(table.index,table[table.columns[i]].values, 'o-',color=custom_colors[i])
            # plt.semilogy(table, 'o-')
            #plt.show()
            plt.ylim([1e-4, 1])
            if 'acr' in testcase or 'ACI' in testcase:
                plt.xlim([-16, 50])
                plt.xlabel('ACR (dB)')
            else:
                plt.xlim([-110, -5])
                plt.xlabel('power (dBm)')
            # plt.xticks(rotation=30)

            plt.ylabel('PER')
            plt.legend(legend_convert,bbox_to_anchor=(1, 1), loc=2, borderaxespad=0, numpoints=1, fontsize=8)
            # plt.legend(legend_convert,loc=1)
            plt.title(testcase + ' '+subfolder_name + ' '+'chan'+str(chan) + ' sensitivity')
            plt.grid();
            x_major_locator = MultipleLocator(5)
            ax = plt.gca()
            plt.subplots_adjust(right=0.8)
            # ax为两条坐标轴的实例
            ax.xaxis.set_major_locator(x_major_locator)
            if not table_evm.empty:
                plt.subplot(2, 1, 2)
                for i in range(len(table_evm.columns)):
                    plt.plot(table_evm.index, table_evm[table_evm.columns[i]].values, 'o-', color=custom_colors[i])
                plt.ylim([-60, 0])
                if 'acr' in testcase or 'ACI' in testcase:
                    plt.xlim([-16, 50])
                    plt.xlabel('ACR (dB)')
                else:
                    plt.xlim([-110, -5])
                    plt.xlabel('power (dBm)')
                # plt.xticks(rotation=30)

                plt.ylabel('EVM(dB)')
                plt.legend(legend_convert, bbox_to_anchor=(1, 1), loc=2, borderaxespad=0, numpoints=1, fontsize=8)
                # plt.legend(legend_convert,loc=1)
                # 取testcase第一个下划线之后的字符串
                plt.title(testcase + ' ' + subfolder_name + '' + 'chan' + str(chan) + ' EVM')
                # plt.title(testcase[2:] + ' ' + subfolder_name + ' ' + 'chan' + str(chan) + ' EVM')
                plt.grid();
                x_major_locator = MultipleLocator(5)
                ax = plt.gca()
                plt.subplots_adjust(right=0.8)
                # ax为两条坐标轴的实例
                ax.xaxis.set_major_locator(x_major_locator)
            # 把x轴的主刻度设置为1的倍数
            #pp = PdfPages(foldername + testcase + '/' + testcase + '_chan'+ str(chan)+ '_Sensitivity.pdf')
            pp.savefig(x1)
            # x_major_locator = MultipleLocator(1)
            # # 把x轴的刻度间隔设置为1，并存在变量里
            # ax.xaxis.set_major_locator(x_major_locator)
            # ax.set_ylabel('per')
            # ax.set_xlabel('rxpwr')
            # ax.legend(loc='upper right', ncol=1, fancybox=True)
            # plt.show()
            # plt.savefig('D:/workspace/fpga/Rx_data/' + testcase + '.png')
            #df.to_csv('D:/model_data.csv')
            # if ' acq2sfd' in df_chan.columns:
            #
    pp.close()
    writer.close()