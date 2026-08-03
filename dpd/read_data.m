function [tx_data, rx_data, adc_data] = read_data(string0)

all_data_table = importfile19(string0, 2, 16385);

all_data_array = table2array(all_data_table);

tx_data0 = all_data_array(:,5)+1j*all_data_array(:,6);
rx_data0 = all_data_array(:,4)+1j*all_data_array(:,3);
adc_data0 = all_data_array(:,1)+1j*all_data_array(:,2);

tx_data = tx_data0(1:2:end,:);
rx_data = rx_data0(1:2:end,:);
adc_data = adc_data0(1:2:end,:);


end