import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal
from scipy.spatial.transform import Rotation as R
from scipy.signal import butter, filtfilt
import warnings
warnings.filterwarnings('ignore')

class MobilePDR:
    def __init__(self):
        self.step_length = 0.7  # Average step length (meters)
        self.heading = 0.0      # Initial heading
        self.position = np.array([0.0, 0.0])  # Initial position
        
        # Step detection parameters
        self.min_step_interval = 0.3  # Minimum step interval (seconds)
        self.acc_threshold = 1.5      # Step detection threshold
        
        # Filter parameters
        self.lowpass_freq = 5.0       # Low-pass filter cutoff frequency
        
    def preprocess_data(self, df):
        """Preprocess IMU data"""
        # Extract data
        timestamps = df.iloc[:, 0].values
        acc_data = df.iloc[:, 1:4].values  # Accelerometer
        gyro_data = df.iloc[:, 4:7].values # Gyroscope
        
        # Calculate sampling frequency
        dt_array = np.diff(timestamps)
        self.dt = np.mean(dt_array)
        self.fs = 1.0 / self.dt
        
        print(f"Sampling frequency: {self.fs:.1f} Hz")
        print(f"Number of data points: {len(timestamps)}")
        
        return timestamps, acc_data, gyro_data
    
    def apply_lowpass_filter(self, data, cutoff_freq=5.0):
        """Apply low-pass filter"""
        if self.fs <= 2 * cutoff_freq:
            cutoff_freq = self.fs / 3
        b, a = butter(4, cutoff_freq / (self.fs / 2), btype='low')
        filtered_data = np.zeros_like(data)
        for i in range(data.shape[1]):
            filtered_data[:, i] = filtfilt(b, a, data[:, i])
        return filtered_data
    
    def detect_steps(self, acc_data):
        """Advanced step detection algorithm"""
        # Calculate vertical acceleration (assume Z axis is vertical)
        acc_vertical = acc_data[:, 2]  # Z axis
        # Apply band-pass filter (0.5-3Hz, human gait frequency range)
        b_high, a_high = butter(4, 0.5 / (self.fs / 2), btype='high')
        b_low, a_low = butter(4, 3.0 / (self.fs / 2), btype='low')
        acc_filtered = filtfilt(b_high, a_high, acc_vertical)
        acc_filtered = filtfilt(b_low, a_low, acc_filtered)
        # Dynamic threshold detection
        window_size = int(0.5 * self.fs)  # 2-second window
        min_peak_height = 1.0  # 可调
        step_indices = []
        for i in range(window_size//2, len(acc_filtered) - window_size//2):
            window_data = acc_filtered[i-window_size//2:i+window_size//2+1]
            threshold = np.std(window_data) * 0.5
            if (acc_filtered[i] > threshold and 
                acc_filtered[i] > min_peak_height and
                acc_filtered[i] > acc_filtered[i-1] and 
                acc_filtered[i] > acc_filtered[i+1]):
                # Check minimum interval
                if not step_indices or (i - step_indices[-1]) > self.min_step_interval * self.fs:
                    step_indices.append(i)
        return np.array(step_indices), acc_filtered
    
    def estimate_heading_from_gyro(self, gyro_data, step_indices):
        """Estimate heading change from gyroscope data"""
        if len(step_indices) < 2:
            return np.zeros(len(step_indices))
        # Use Z-axis angular rate (yaw)
        yaw_rate = gyro_data[:, 2] * np.pi / 180  # Convert to radians
        # Integrate angular rate to get heading change
        headings = []
        current_heading = self.heading
        for i, step_idx in enumerate(step_indices):
            if i == 0:
                # Use gyro data from start to first step
                yaw_change = np.trapz(yaw_rate[:step_idx], dx=self.dt)
                current_heading += yaw_change
                headings.append(current_heading)
            else:
                prev_step = step_indices[i-1]
                yaw_change = np.trapz(yaw_rate[prev_step:step_idx], dx=self.dt)
                current_heading += yaw_change
                headings.append(current_heading)
        return np.array(headings)
    
    def adaptive_step_length(self, acc_data, step_indices):
        """Adaptive step length estimation"""
        if len(step_indices) < 2:
            return np.full(len(step_indices), self.step_length)
        step_lengths = []
        for i, step_idx in enumerate(step_indices):
            if i == 0:
                step_lengths.append(self.step_length)
            else:
                # Estimate step length based on acceleration peak
                prev_step = step_indices[i-1]
                acc_window = acc_data[prev_step:step_idx]
                acc_magnitude = np.sqrt(np.sum(acc_window**2, axis=1))
                # Simple step length model: based on acceleration peak
                peak_acc = np.max(acc_magnitude) - np.min(acc_magnitude)
                estimated_length = 0.4 + 0.3 * (peak_acc / 10.0)  # Empirical formula
                estimated_length = np.clip(estimated_length, 0.3, 1.2)  # Limit to reasonable range
                step_lengths.append(estimated_length)
        return np.array(step_lengths)
    
    def calculate_trajectory(self, df):
        """Calculate pedestrian trajectory"""
        print("Processing data...")
        # Preprocess data
        timestamps, acc_data, gyro_data = self.preprocess_data(df)
        # Apply filtering
        acc_filtered = self.apply_lowpass_filter(acc_data, self.lowpass_freq)
        gyro_filtered = self.apply_lowpass_filter(gyro_data, self.lowpass_freq)
        print("Detecting steps...")
        # Step detection
        step_indices, acc_signal = self.detect_steps(acc_filtered)
        print(f"Detected {len(step_indices)} steps")
        if len(step_indices) < 2:
            print("Too few steps detected, cannot calculate trajectory")
            return None
        # Estimate heading
        headings = self.estimate_heading_from_gyro(gyro_filtered, step_indices)
        # Estimate step length
        step_lengths = self.adaptive_step_length(acc_filtered, step_indices)
        # Calculate trajectory
        trajectory = [self.position.copy()]
        current_pos = self.position.copy()
        for i in range(1, len(step_indices)):
            # Calculate displacement based on heading and step length
            dx = step_lengths[i] * np.cos(headings[i])
            dy = step_lengths[i] * np.sin(headings[i])
            current_pos[0] += dx
            current_pos[1] += dy
            trajectory.append(current_pos.copy())
        trajectory = np.array(trajectory)
        # Return results
        results = {
            'trajectory': trajectory,
            'step_indices': step_indices,
            'step_times': timestamps[step_indices],
            'step_lengths': step_lengths,
            'headings': headings,
            'acc_signal': acc_signal,
            'total_distance': np.sum(step_lengths)
        }
        return results
    
    def plot_results(self, results, timestamps, acc_data):
        """Plot results"""
        if results is None:
            print("No results to plot")
            return
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        # 1. Trajectory plot
        trajectory = results['trajectory']
        ax1.plot(trajectory[:, 0], trajectory[:, 1], 'b-o', markersize=4, linewidth=2)
        ax1.plot(trajectory[0, 0], trajectory[0, 1], 'go', markersize=10, label='Start')
        ax1.plot(trajectory[-1, 0], trajectory[-1, 1], 'ro', markersize=10, label='End')
        ax1.set_xlabel('X (m)')
        ax1.set_ylabel('Y (m)')
        ax1.set_title('Estimated Trajectory')
        ax1.grid(True)
        ax1.axis('equal')
        ax1.legend()
        # 2. Acceleration signal and step detection
        time_axis = timestamps - timestamps[0]
        ax2.plot(time_axis, results['acc_signal'], 'b-', alpha=0.7, label='Filtered Signal')
        step_times = results['step_times'] - timestamps[0]
        step_signal_values = results['acc_signal'][results['step_indices']]
        ax2.plot(step_times, step_signal_values, 'ro', markersize=6, label=f'Step Detection ({len(results["step_indices"])} steps)')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Acceleration Signal')
        ax2.set_title('Step Detection Results')
        ax2.grid(True)
        ax2.legend()
        # 3. Step length variation
        ax3.plot(range(len(results['step_lengths'])), results['step_lengths'], 'g-o', markersize=4)
        ax3.set_xlabel('Step Number')
        ax3.set_ylabel('Step Length (m)')
        ax3.set_title('Step Length Estimation')
        ax3.grid(True)
        # 4. Heading variation
        headings_deg = results['headings'] * 180 / np.pi
        ax4.plot(range(len(headings_deg)), headings_deg, 'm-o', markersize=4)
        ax4.set_xlabel('Step Number')
        ax4.set_ylabel('Heading (deg)')
        ax4.set_title('Heading Estimation')
        ax4.grid(True)
        plt.tight_layout()
        plt.show()
        # Print statistics
        print(f"\n=== Trajectory Statistics ===")
        print(f"Total steps: {len(results['step_indices'])}")
        print(f"Total distance: {results['total_distance']:.2f} m")
        print(f"Average step length: {np.mean(results['step_lengths']):.2f} m")
        print(f"Step length range: {np.min(results['step_lengths']):.2f} - {np.max(results['step_lengths']):.2f} m")
        final_pos = trajectory[-1]
        displacement = np.sqrt(final_pos[0]**2 + final_pos[1]**2)
        print(f"Start-End displacement: {displacement:.2f} m")


def main():
    """Main function"""
    # Read data
    print("Reading data...")
    # Please replace with your data file path
    # df = pd.read_csv("data/iPhoneDemoStra.csv")  # Modify file path as needed
    df = pd.read_csv("data/RoundTrip.csv")  # Modify file path as needed
    # Create PDR object
    pdr = MobilePDR()
    # Parameter adjustment (if needed)
    pdr.step_length = 0.65      # Adjust average step length
    pdr.acc_threshold = 1.2     # Adjust step detection sensitivity
    pdr.min_step_interval = 0.4 # Adjust minimum step interval
    # Calculate trajectory
    results = pdr.calculate_trajectory(df)
    if results is not None:
        # Plot results
        timestamps, acc_data, _ = pdr.preprocess_data(df)
        pdr.plot_results(results, timestamps, acc_data)
    return results

if __name__ == "__main__":
    results = main()