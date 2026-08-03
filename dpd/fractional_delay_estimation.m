function [pa_data_after_fractional_delay_comp] = fractional_delay_estimation(tx_data_norm, pa_data_after_cfo_comp)

% fractional delay estimation
tx_data_temp = tx_data_norm(1:630,:);
rx_data_temp = pa_data_after_cfo_comp(1:630,:);

conv_results = abs(conv(tx_data_temp,rx_data_temp));
[max_value,max_index] = max(conv_results);
xx1 = (1:length(conv_results)).';
figure;
plot(xx1,conv_results);hold on;
xlim([626,634]);
ylim([max_value*9/10,max_value*11/10]);

y0 = conv_results(max_index-1,:);
y1 = conv_results(max_index,  :);
y2 = conv_results(max_index+1,:);

a = (y2+y0-2*y1)/2;
b = (y2-y0)/2;
c = y1;
xx = (1:0.01:length(conv_results)).';
yy = a*(xx-max_index).^2+b*(xx-max_index)+c;
plot(xx,yy,'color','r');

frac_delay = -b/(2*a);

% fractional compensation for real data
input_x = (1:length(pa_data_after_cfo_comp)).';
output_x = input_x+frac_delay;
pa_data_after_fractional_delay_comp = interp1(input_x,pa_data_after_cfo_comp,output_x,'spline');

% fractional compensation for STF data
input_x0 = (1:length(rx_data_temp)).';
output_x0 = input_x0+frac_delay;
rx_data_temp_after_fractional_delay_comp = interp1(input_x0,rx_data_temp,output_x0,'spline');

stf_conv_results_after_delay_comp = abs(conv(tx_data_temp,rx_data_temp_after_fractional_delay_comp));
figure;plot(stf_conv_results_after_delay_comp);
xlim([626,634]);
title('After fractional delay compensation')

end




