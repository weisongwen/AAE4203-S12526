clc;
clear;
close all;

addpath( fullfile('matRTKLIB') )

%% Read RINEX observation/navigation file
obs = gt.Gobs(fullfile('COM6___9600_250916_020025_blockz.obs'));
nav = gt.Gnav(fullfile('COM6___9600_250916_020025_blockz.nav'));
obs.plot;
obs.plotNSat;
obs.plotSky(nav);

%% Settings for position computation
SNR_TH = 15; % SNR threshold (dBHz)
EL_TH = 10; % Elevation angle threshold (deg)
obs.maskP(obs.L1.S<SNR_TH);


%% Initials
num_epochs = size(obs.L1.P, 1); % 
nx = 3+1; % Position in ECEF and receiver clock [x,y,z,dtr]'
x = zeros(nx,1); % Initial position is center of the Earth
xlog = zeros(obs.n,nx); % For logging solution
xlog_llh=zeros(obs.n,3); % For logging solution in LLH
llhref= [22.304139,114.180131,-20.20];
%% Initialize cell arrays to store data for each epoch
pseudoranges_meas_cell = cell(num_epochs, 1); % 
satellite_positions_cell = cell(num_epochs, 1); % 
satellite_clock_bias_cell = cell(num_epochs, 1); % 
ionospheric_delay_cell = cell(num_epochs, 1); % 
tropospheric_delay_cell = cell(num_epochs, 1); % 
doppler_meas_cell = cell(num_epochs, 1); % 

%% Loop over all epochs
%% Point positioning

for epoch = 1:num_epochs
    obsc = obs.selectTime(epoch); % Current observation
    satc = gt.Gsat(obsc,nav); % Compute satellite position

    % Repeat until convergence
    for iter = 1:100
        satc.setRcvPos(gt.Gpos(x(1:3)',"xyz")); % Set current receiver position
        obsc = obsc.residuals(satc); % Compute pseudorange residuals at current position

        % resP = obs.P-(rng-dts+ion+trp)-dtr-tgd
        resP = obsc.L1.resPc-x(4)-nav.getTGD(satc.sat);

        idx = ~isnan(resP) & satc.el>EL_TH; % Index not NaN
        nobs = nnz(idx); % Number of current observation

        % Simple elevation angle dependent weight model
        varP90 = 0.5^2;
        w = 1./(varP90./sind(satc.el(idx))); 
        sys = obsc.sys(idx);

        % Design matrix
        H = zeros(nobs,nx);
        H(:,1) = -satc.ex(idx)'; % LOS vector in ECEF X
        H(:,2) = -satc.ey(idx)'; % LOS vector in ECEF Y
        H(:,3) = -satc.ez(idx)'; % LOS vector in ECEF Z
        H(:,4) = 1.0;           % Reciever clock

        % Weighted least square
        % (y-H*x)'*diag(w)*(y-H*x)
        y = resP(idx)';
        dx = lscov(H,y,w); % position/clock error

        % Solution correction
        x = x+dx;

        % Exit loop after convergence 
        if norm(dx)<1e-3
            break;
        end
    end
    xlog(epoch,:) = x';
    fprintf("epoch=%d iter:%d\n",epoch,iter);
    %% Extract the raw measurement for current epoch
    p_l1 = obsc.L1.P;
    sat_prn = obsc.sat; % Remove epoch indexing
    sat_pos_x = satc.x;
    sat_pos_y = satc.y;
    sat_pos_z = satc.z;
    sat_pos = [sat_pos_x; sat_pos_y; sat_pos_z];
    sat_clock_err = satc.dts;
    sat_pos = transpose(sat_pos);
    p_l1 = transpose(p_l1);
    sat_clock_err = transpose(sat_clock_err);
    ion_error_l1 = satc.ionL1;
    ion_error_l1 = transpose(ion_error_l1);
    tropo_error = satc.trp;
    tropo_error = transpose(tropo_error);
    sat_sys = satc.sys; % Remove epoch indexing

    %% Exclude NaN values
    valid_idx = ~isnan(p_l1) & ~isnan(sat_pos(:,1)) & ~isnan(sat_pos(:,2)) & ~isnan(sat_pos(:,3));
    p_l1 = p_l1(valid_idx);
    sat_prn = sat_prn(valid_idx);
    sat_pos = sat_pos(valid_idx,:);
    sat_clock_err = sat_clock_err(valid_idx);
    ion_error_l1 = ion_error_l1(valid_idx);
    tropo_error = tropo_error(valid_idx);
    sat_sys = sat_sys(valid_idx);



    %% Save data into cell arrays
    pseudoranges_meas_cell{epoch} = p_l1;
    satellite_positions_cell{epoch} = sat_pos; % Nx3 matrix
    satellite_clock_bias_cell{epoch} = sat_clock_err;
    ionospheric_delay_cell{epoch} = ion_error_l1;
    tropospheric_delay_cell{epoch} = tropo_error;

    %% Correct pseudorange measurements
    p_l1_corrected = p_l1 + sat_clock_err - ion_error_l1 - tropo_error;


end

%% After processing all epochs, write the data to CSV files

% Find the maximum number of satellites across all epochs
max_num_sats = max(cellfun(@(x) size(x,1), pseudoranges_meas_cell));

% Initialize matrices with NaNs
pseudoranges_meas_mat = NaN(max_num_sats, num_epochs);
satellite_clock_bias_mat = NaN(max_num_sats, num_epochs);
ionospheric_delay_mat = NaN(max_num_sats, num_epochs);
tropospheric_delay_mat = NaN(max_num_sats, num_epochs);
satellite_positions_mat = NaN(max_num_sats, num_epochs*3); % 3 columns per epoch

% Fill the matrices with data from cell arrays
for epoch = 1:num_epochs
    p_l1 = pseudoranges_meas_cell{epoch};
    sat_clock_err = satellite_clock_bias_cell{epoch};
    ion_error_l1 = ionospheric_delay_cell{epoch};
    tropo_error = tropospheric_delay_cell{epoch};
    sat_pos = satellite_positions_cell{epoch};

    num_sats = length(p_l1);

    pseudoranges_meas_mat(1:num_sats, epoch) = p_l1;
    satellite_clock_bias_mat(1:num_sats, epoch) = sat_clock_err;
    ionospheric_delay_mat(1:num_sats, epoch) = ion_error_l1;
    tropospheric_delay_mat(1:num_sats, epoch) = tropo_error;

    satellite_positions_mat(1:num_sats, (epoch-1)*3+1 : epoch*3) = sat_pos;
end

% Write the matrices to CSV files
writematrix(pseudoranges_meas_mat, 'pseudoranges_meas.csv');
writematrix(satellite_clock_bias_mat, 'satellite_clock_bias.csv');
writematrix(ionospheric_delay_mat, 'ionospheric_delay.csv');
writematrix(tropospheric_delay_mat, 'tropospheric_delay.csv');
writematrix(satellite_positions_mat, 'satellite_positions.csv');

%% Convert ECEF positions to LLH
xlog_llh = ecef2lla(xlog(:,1:3), 'WGS84'); % [lat, lon, height] in degrees and meters

%% Plot calculated receiver positions on a map
posest = gt.Gpos(xlog(:,1:3),'xyz');
posest.setOrg(llhref,"llh");
posest.plot;
title('LSE Trajectory');

% %% RTKLIB spp solution
% opt=gt.Gopt("spp.conf");
% sol=gt.Gfun.pntpos(obs,nav,opt);
% pos_spp_rtklib=gt.Gpos(sol.pos.llh,'llh');
% pos_spp_rtklib.setOrg(llhref,"llh");
% pos_spp_rtklib.plot;
% title('RTKLIB SPP Trajectory');
