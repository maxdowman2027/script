function amamplot(ref_data,rx_data,tableX,tableY,names1)

x = ref_data;
y = rx_data;

numLUT = size(tableY,2);

tableX = [0;tableX];
tableY = [zeros(1,numLUT);tableY];

figure;
h(1,:) = plot(abs(x),abs(y),'marker','o','linestyle','none');hold on;
legendNames{1} = 'PA';
for n = 1:numLUT
    h(n+1,:)=plot(abs(tableX),abs(tableY(:,n)),'linewidth',4);hold on
    legendNames{n+1} = ['LUT index',num2str(n)];
end

title([names1,', AM-AM curve']);
axis equal;
grid on;
grid minor;
xlim([0,1500]);
ylim([0,1500]);
xlabel('AM');
ylabel('AM');
legend(h,legendNames);

figure;
%plot(abs(x),atan(y./x),'marker','o','linestyle','none');
% phase1 = imag(y./x)./real(y./x);
phase1 = y.*conj(x);
% coef = polyfit(1500:2000,phase(phase1(1500:2000)).',1);
phase2 = phase1;
h(1,:)= plot(abs(x),atan(imag(phase2)./real(phase2)),'marker','o','linestyle','none');hold on;
legendNames{1} = 'PA';
phaseCoef = polyfit(abs(x),atan(imag(phase2)./real(phase2)),2);
xx = (1:1023).';
yy =phaseCoef(:,3)+phaseCoef(:,2)*xx+phaseCoef(:,1)*xx.^2;
h(2,:) = plot(xx,yy,'LineStyle','-','color','green','linewidth',2);
legendNames{2} = 'PA fit';
tableY(2,:) = real(tableY(2,:));
for n = 1:numLUT
    h(n+2,:) = plot(abs(tableX),atan(imag(tableY(:,n))./real(tableY(:,n))),'linewidth',4);hold on;
    legendNames{n+2} = ['LUT index',num2str(n)];
end
xlabel('AM');
ylabel('PM');
legend(h,legendNames);
title([names1,', AM-PM curve']);


end




