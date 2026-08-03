function [pa_data_after_cfo_comp] = frequency_offset_estimation(tx_data_norm, pa_data_norm)

% CFO estimation using polyfit
corr_result = tx_data_norm(1:3500,:).*conj(pa_data_norm(1:3500,:));
phase1 = phase(corr_result);
figure;plot(phase1);hold on;
title('Phase of Tx and PA data correlation results, before CFO compensation');

x = (1:length(corr_result)).';
coef1 = polyfit(x,phase1,1);
x1 = (1:length(pa_data_norm)).';
fit_result = coef1(1)*x1+coef1(2);
plot(fit_result,'linewidth',4,'color','r');

% CFR compensation
pa_data_after_cfo_comp = pa_data_norm.*exp(1j*(fit_result));

corr_result_after_comp = tx_data_norm.*conj(pa_data_after_cfo_comp);
phase2 = phase(corr_result_after_comp);

figure;plot(phase2);hold on;


coef2 = polyfit(x1,phase2,1);
fit_result2 = coef2(1)*x1+coef2(2);
plot(fit_result2,'linewidth',4,'color','r');

end