clc;
clear;


psdPlotFlag       = 1;
wavePlotFlag      = 1;
rawDataPlotFlag   = 1;
gainDataPlotFlag  = 0;
cfoDataPlotFlag   = 0;
dcDataPlotFlag    = 0;
delayDataPlotFlag = 0;

% load data
% string0 = '1023_1_gain158_feedback_ref_iladata.csv';
string0 = 'gain168_test_data_3.csv';
%string1 = 'gain168_iqxel_data.txt';
% read raw data
[tx_data, rx_data, adc_data] = read_data(string0);
tx_data = tx_data(89:end,:);

% pa_data =load('gain168_iqxel_short_data.mat');
% pa_data = pa_data.pa_data(1:length(tx_data),:);

rx_data =load('gain168_iqxel_short_data.mat');
rx_data = rx_data.pa_data(1:length(tx_data),:);
% pa_data = load('gain168_iqxel_data.txt');
% pa_data = pa_data(1:6:16384*6,:);
% pa_data = pa_data(:,1)+1j*pa_data(:,2);
tx_data_temp = tx_data(231:231+630-1,:);
rx_data_temp = rx_data(231:231+630-1,:);

% tx_data = tx_data(1250:7000,:);
% rx_data = rx_data(1250:7000,:);

tx_data = tx_data(231:7000,:);
rx_data = rx_data(231:7000,:);

% gain compensation
[tx_data_gain, rx_data_gain] = gain_compensation(tx_data, rx_data);

Niter = 1;

for n = 1:Niter
% carrier frequency offset estimation and compensation
[pa_data_after_cfo_comp] = frequency_offset_estimation(tx_data_gain, rx_data_gain);
%pa_data_after_cfo_comp = pa_data_gain;

% DC compensation
[tx_data_dc, rx_data_dc] = dc_compensation(tx_data, pa_data_after_cfo_comp);


% frac delay compensation
[rx_data_after_fractional_delay_comp] = fractional_delay_estimation(tx_data_dc, rx_data_dc);

rx_data_gain = rx_data_after_fractional_delay_comp;
end

% static DPD
maxTableValue = 1023;
% [tableX, tableY] = static_DPD(maxTableValue,tx_data_gain,rx_data_after_fractional_delay_comp);
numLUT = 1;
estDelay = 0;
order  = 3;

tx_data_gain = tx_data_gain(1000:end,:);
rx_data_after_fractional_delay_comp = rx_data_after_fractional_delay_comp(1000:end,:);
[tableX, tableY] = static_DPD_memory(maxTableValue,tx_data_gain,rx_data_after_fractional_delay_comp,numLUT,estDelay,order);


amamplot(tx_data_gain,rx_data_after_fractional_delay_comp,tableX,tableY,'PA-Rx');











