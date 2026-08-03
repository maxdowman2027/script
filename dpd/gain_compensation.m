function [tx_data_gain, rx_data_gain] = gain_compensation(tx_data_dc, rx_data_dc)


[location, ~] = find(abs(tx_data_dc)<1000);

tx_rms = sqrt(mean(abs(tx_data_dc(location,:)).^2));
rx_rms = sqrt(mean(abs(rx_data_dc(location,:)).^2));

tx_data_gain = tx_data_dc;
rx_data_gain = rx_data_dc*tx_rms/rx_rms;


end