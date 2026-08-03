function [tx_data_dc, rx_data_dc] = dc_compensation(tx_data, rx_data)

startPoint = 600;
L    =  256;

tx_dc_est = mean(tx_data(startPoint:startPoint+L-1,:));
rx_dc_est = mean(rx_data(startPoint:startPoint+L-1,:));

tx_data_dc = tx_data-tx_dc_est;
rx_data_dc = rx_data-rx_dc_est;

% just for DC test
% all_length = length(rx_data);
% dc_est_vec = zeros(all_length-L-1-startPoint,1);
% 
% for n = 1:length(dc_est_vec)
%       dc_est_vec(n,:)  =  mean(tx_data(startPoint+n-1:startPoint+L-1+n-1,:));
% end
% 
% figure;plot(real(dc_est_vec));hold on;
% plot(imag(dc_est_vec));
end
