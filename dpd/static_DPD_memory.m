function [tableX, tableY] = static_DPD_memory(maxTableValue,x,y,numLUT,estDelay,order)

tableSize = 32;
delta = maxTableValue/tableSize;
tableX = (delta:delta:maxTableValue).';

L = size(y,1);
Y = zeros(L,order*numLUT);
X = [zeros(estDelay,1);x(1:end-estDelay,:)];

for k = 1:numLUT
    yDelay = [zeros(k-1,1);y(1:end-(k-1))];
    for m = 1:order
        Y(:,(k-1)*order+m) = yDelay.*abs(yDelay).^(m-1);
    end
end

coefEst = (Y'*Y)^(-1)*(Y')*X;

x1 = repmat(tableX,1,numLUT);
tableY = zeros(32,numLUT);
for k = 1:numLUT
   for m = 1:order
       tableY(:,k) = tableY(:,k) + coefEst((k-1)*order+m,:)*(x1(:,k).^m); 
   end
end


end