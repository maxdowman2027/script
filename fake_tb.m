close;clc;clear all;
%% input
ru_alloc_list = [26,52,106,242,484,996,1992];

%% input argv here

ul_bw = 0;  %used to choose mmss
ru_allocation = 52;  % as ele of ru_alloc_list
apep_len = 142;
last_mpdu_len = 138;
ul_mcs = 5;
ul_nss = 2;  %index from 1
ul_coding = 0;  %constrainted by bw/mcs
ul_gi_ltf = 1;  %1x 1.6/2x 1.6/4x 3.2
ul_num_ltf = 1;  % 0/1/2/3/4 represents for 1/2/4/6/8 HE-LTFs
ul_dcm = 0;
ul_stbc = 0;
nominal_packet_padding = 0;
bss_color = randi([1,63]);
txop = 127;  %don't care,hesiga2 default set to all 1's

%% tmp var
ul_ru = find(ru_alloc_list == ru_allocation) - 1;  %index from 0
if(mod(last_mpdu_len,4) == 0)
    last_mpdu_padding = 0;
else
    last_mpdu_padding = 4 - mod(last_mpdu_len,4);
end

if(ul_gi_ltf == 0)
    he_ltf_txtime = 4.8;
    sym_txtime = 14.4;
    gi_type = 2;
    ltf_type = 0;
elseif(ul_gi_ltf == 1)
    he_ltf_txtime = 8;
    sym_txtime = 14.4;
    gi_type = 2;
    ltf_type = 1;
else
    he_ltf_txtime = 16;
    sym_txtime = 16;
    gi_type = 3;
    ltf_type = 2;
end

switch ul_num_ltf
    case 0
        num_ltf = 1;
    case 1
        num_ltf = 2;
    case 2
        num_ltf = 4;
    case 3
        num_ltf = 6;
    case 4
        num_ltf = 8;
    otherwise
        ;
end
nsd_1lax = [24,48,102,234,468,980,1960
            12,24,51,117,234,490,980];  %DCM=0/1
nsd_short = [6,12,24,60,120,240,492
             2,6,12,30,60,120,246];  %DCM=0/1

r_bpscs = [1,2,2,4,4,6,6,6,8,8,10,10];
r_x12 = [6,6,9,6,9,8,9,10,9,10,9,10];
n_dbps = floor(nsd_1lax(ul_dcm+1,ul_ru+1)*r_x12(ul_mcs+1)*n_bpscs(ul_mcs+1)/12*ul_nss);
n_cbps = nsd_1lax(ul_dcm+1,ul_ru+1)*n_bpscs(ul_mcs+1)*ul_nss;
n_cbps_short = nsd_short(ul_dcm+1,ul_ru+1)*n_bpscs(ul_mcs+1)*ul_nss;
n_dbps_short = n_cbps_short*r_x12(ul_mcs+1)/12;

if(ul_stbc == 1)
    m_stbc = 2;
else
    m_stbc = 1;
end

%% calc
if(ul_coding)
    n_sym_init = ceil((8*apep_len+16)/(m_stbc*n_dbps))*m_stbc;
    n_excess = mod(8*apep_len+16,m_stbc*n_dbps);
else
    n_sym_init = ceil((8*apep_len+16+6)/(m_stbc*n_dbps))*m_stbc;
    n_excess = mod(8*apep_len+16+6,m_stbc*n_dbps);
end
if(n_excess == 0)
    a_init = 4;
else
    a_init = min(4,ceil(n_excess/(m_stbc*n_dbps_short)));
end

if(a_init == 4)
    n_dbps_last_init = n_dbps;
    n_cbps_last_init = n_cbps;
else
    n_dbps_last_init = a_init * n_dbps_short;
    n_cbps_last_init = a_init * n_cbps_short;
end
n_pld = (n_sym_init - m_stbc)*n_dbps+m_stbc*n_dbps_last_init;
n_avbits = (n_sym_init - m_stbc)*n_cbps+m_stbc*n_cbps_last_init;
if(n_avbits <= 648)
    n_cw = 1;
elseif(n_avbits <= 1296)
    n_cw = 1;
elseif(n_avbits <= 1944)
    n_cw = 1;
elseif(n_avbits <= 2592)
    n_cw = 2;
else
    n_cw = ceil(n_pld/(1944*r_x12(ul_mcs+1)/12));
end

if((n_pld+912*(12-r_x12(ul_mcs+1))/12) > n_avbits && (n_pld+912*(12-r_x12(ul_mcs+1))/12) <= 648)
    l_ldpc = 648;
    l_ldpc_code = 0;
elseif(n_pld+912*(12-r_x12(ul_mcs+1))/12) <= n_avbits && n_avbits <= 648)
    l_ldpc = 1296;
    l_ldpc_code = 1;
elseif(n_avbits > 648 && n_avbits < (n_pld+1464*(12-r_x12(ul_mcs+1))/12))
    l_ldpc = 1296;
    l_ldpc_code = 1;
elseif(n_pld+1464*(12-r_x12(ul_mcs+1))/12) <= n_avbits && n_avbits <= 1944)
    l_ldpc = 1944;
    l_ldpc_code = 2;
elseif(n_avbits > 1944 && n_avbits < (n_pld+2916*(12-r_x12(ul_mcs+1))/12))
    l_ldpc = 1296;
    l_ldpc_code = 1;
elseif(n_avbits >= 1944 && n_avbits <= (n_pld+2916*(12-r_x12(ul_mcs+1))/12))
    l_ldpc = 1944;
    l_ldpc_code = 2;
end
n_short = max(0,n_cw*l_ldpc*r_x12(ul_mcs+1)/12-n_pld);
n_punc = max(0,n_cw*l_ldpc-n_avbits-n_short);
if(n_punc > 0.1*n_cw*l_ldpc*(12-r_x12(ul_mcs+1))/12 && n_short < 1.2*n_punc*r_x12(ul_mcs+1)/(12-r_x12(ul_mcs+1)))
    ldpc_extra_sym = 1;
    if(a_init == 3)
        n_avbits = n_avbits + m_stbc*(n_cbps-3*n_cbps_short);
        n_punc = max(0,n_cw*l_ldpc-n_avbits-n_short);
    else
        n_avbits = n_avbits + m_stbc*n_cbps_short;
        n_punc = max(0,n_cw*l_ldpc-n_avbits-n_short);
    end
elseif(n_punc > 0.3*n_cw*l_ldpc*(12-r_x12(ul_mcs+1))/12)
    ldpc_extra_sym = 1;
    if(a_init == 3)
        n_avbits = n_avbits + m_stbc*(n_cbps-3*n_cbps_short);
        n_punc = max(0,n_cw*l_ldpc-n_avbits-n_short);
    else
        n_avbits = n_avbits + m_stbc*n_cbps_short;
        n_punc = max(0,n_cw*l_ldpc-n_avbits-n_short);
    end
else
    ldpc_extra_sym = 0;
end
if(ul_coding && ldpc_extra_sym)
    if(a_init == 4)
        n_sym = n_sym_init + m_stbc;
        a_factor = 1;
    else
        n_sym = n_sym_init;
        a_factor = a_init + 1;
    end
else
    n_sym = n_sym_init;
    a_factor = a_init;
end
t_preamble = 20+4+8+8+num_ltf*he_ltf_txtime;
if(nominal_packet_padding == 0)
    t_pe = 0;
elseif(nominal_packet_padding == 8)
    if(a_factor < 3)
        t_pe = 0;
    elseif(a_factor == 3)
        t_pe = 4;
    else
        t_pe = 8;
    end
elseif(nominal_packet_padding == 16)
    t_pe = 4*a_factor;
else  %abnormal
    t_pe = 0;
end

txtime = t_preamble + n_sym*sym_txtime+t_pe;
if(4*(ceil((txtime-20)/4)) - ((txtime-20)/4)+t_pe >= sym_txtime)
    pe_disambiguity = 1;
else
    pe_disambiguity = 0;
end

l_len = ceil((txtime-20)/4)*3-3-2;
if(ul_coding)
    psdu_len = floor((n_pld - 16)/8);
    pre_fec_padding_phy = mod(n_pld - 16,8);
else
    psdu_len = floor((n_pld - 16 - 6)/8);
    pre_fec_padding_phy = mod(n_pld - 16 - 6,8);
end
n_short_per_ncw = floor(n_short/n_cw);
n_short_mod_ncw = mod(n_short,n_cw);
n_repeat = max(n_avbits-n_cw*l_ldpc*(12-r_x12(ul_mcs+1))/12-n_pld,0);
if(n_repeat > 0)
    ldpc_repeat_punc_ind = 1;
else
    ldpc_repeat_punc_ind = 0;
end
if(ldpc_repeat_punc_ind)
    n_repeat_punc_per_cw = floor(n_repeat/n_cw);
    n_repeat_punc_mod_cw = mod(n_repeat,n_cw);
else
    n_repeat_punc_per_cw = floor(n_punc/n_cw);
    n_repeat_punc_mod_cw = mod(n_punc,n_cw);
end

pre_fec_padding_mac = psdu_len - apep_len;
if(pre_fec_padding_mac > last_mpdu_padding)
    pre_fec_padding_mac = pre_fec_padding_mac - last_mpdu_padding;
    pre_fec_padding_mac_ena = 1;
else
    pre_fec_padding_mac_ena = 0;
end

%% print all reg_input

fprintf('reg_faketb_a_factor=%d\n',a_factor);
fprintf('0xc302249c=0x%x\n',bitor(bitshift(1,31), ...
    bitor(bitshift(0,23), ...
    bitor(bitshift(0,22), ...
    bitor(bitshift(0,21), ...
    bitor(bitshift(74,13), ...  % !!need to modify real ru_allocation here!!!
    bitor(bitshift(ul_coding,12), ...
    bitor(bitshift(0,9), ...
    bitor(bitshift(ul_num_ltf,6), ...
    bitor(bitshift(0,5), ...
    bitor(bitshift(ul_nss+ul_stbc-1,2), ul_gi_ltf)))))))))));

fprintf('0xc30224a0=0x%x\n',bitor(bitshift(pre_fec_padding_phy,27), ...
    bitor(bitshift(0,12),n_sym)));

fprintf('0xc30224a4=0x%x\n',bitor(bitshift(pre_fec_padding_mac_ena,21), pre_fec_padding_mac));

fprintf('0xc30224a8=0x%x\n',bitor(bitshift(ul_stbc,31), ...
    bitor(bitshift(t_pe,26), ...
    bitor(bitor(bitor(bitor(bitor(bitshift(bss_color,1), ...
    bitshift(15,7)), ...  %spatial_reuse
    bitshift(15,11)), ...  %spatial_reuse
    bitshift(15,15)), ...  %spatial_reuse
    bitshift(15,19)), ...  %spatial_reuse
    bitshift(ul_bw,24)))));

fprintf('0xc30224ac=0x%x\n',bitor(bitshift(a_factor,23), ...
    bitor(bitshift(l_ldpc_code,21), ...
    bitor(bitshift(pe_disambiguity,20), ...
    bitor(bitshift(ul_mcs,16), ...
    bitor(bitshift(0,15), ...
    bitor(bitshift(3,13), ...
    bitor(bitshift(ul_dcm,12), l_len))))))));

fprintf('0xc30224b0=0x%x\n',psdu_len);
fprintf('0xc30224b4=0x%x\n',bitor(bitshift(65535,16), ...
    bitor(bitshift(ldpc_extra_sym,14),n_cw)));
fprintf('0xc30224b8=0x%x\n',bitor(bitshift(n_short_mod_ncw,14),n_short_per_ncw));
fprintf('0xc30224bc=0x%x\n',bitor(bitshift(ldpc_repeat_punc_ind,28), ...
    bitor(bitshift(n_repeat_punc_mod_cw,14),n_repeat_punc_per_cw)));