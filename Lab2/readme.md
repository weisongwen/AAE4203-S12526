# AAE4203 Laboratory 2: Inertial Navigation and PDR

## The Hong Kong Polytechnic University

**Department of Aeronautical and Aviation Engineering**
**2025/26 Semester 1**

- **Laboratory Date:** 3rd November 2025, 8:30-11:30
- **Lab Report Due Date:** Before 17th November 2025, 23:59

---

## 1. Objective

The objective of this laboratory is to provide students with hands-on experience in **IMU-based pedestrian positioning**. Students will learn to collect sensor data from a smartphone, process it using a **Pedestrian Dead-Reckoning (PDR)** algorithm, and implement **adaptive step detection** to achieve accurate trajectory estimation. This lab focuses on understanding the theoretical principles of step-based navigation and the practical effects of parameter tuning on positioning accuracy.

---

## 2. Theoretical Background

### 2.1 Pedestrian Dead-Reckoning (PDR)

PDR is a step-based navigation technique that estimates pedestrian position by detecting individual steps and calculating displacement based on step length and heading direction. 

The PDR algorithm consists of three main components:

- **Step Detection:** Identifying when a step occurs using accelerometer data
- **Step Length Estimation:** Calculating the distance covered in each step
- **Heading Estimation:** Determining the direction of movement using gyroscope data

### 2.2 Adaptive Step Detection

Traditional step detection uses fixed thresholds, which may fail under different walking conditions. The adaptive approach dynamically adjusts detection thresholds based on local signal characteristics:

1. **Band-pass Filtering:** Isolates the 0.5-3Hz frequency range typical of human gait
2. **Dynamic Thresholding:** Uses local signal variance to set detection thresholds
3. **Peak Detection:** Identifies step events as local maxima above the adaptive threshold
4. **Temporal Constraints:** Enforces minimum step intervals to prevent false detections

This adaptive approach makes the algorithm robust to different users, walking speeds, and phone orientations.

### 2.3 Heading Estimation from Gyroscope

The pedestrian's heading is estimated by integrating the Z-axis angular velocity from the gyroscope:

```
θ(k) = θ(k-1) + ∫ ωz(t) dt
```

This integration provides the cumulative heading change between consecutive steps, allowing the algorithm to track direction changes during walking.

### 2.4 Adaptive Step Length Model

Step length is estimated using an empirical model that correlates acceleration characteristics with step size. The model considers the peak-to-peak acceleration variation within each step interval:

```
Step Length = base_length + scaling_factor × (acceleration_variation)
```

This approach allows the algorithm to adapt to different walking styles and speeds.

---

## 3. Laboratory Procedure

### 3.1 Step 1: Data Collection

You will use the provided [HTML IMU data collection demo](https://yogurt-ybn.github.io/PDR_website/) to record sensor data from your smartphone. At the same time, we also provide two datasets `RoundTrip.csv` and `Square.csv` in data folder for students to use.

1. **Define a Path:** Plan a simple, repeatable path, such as walking in a square of 5×5 meters or walking 10 meters straight, turning around, and returning to the start.
2. **Collect Data:** Open the HTML demo on your phone, start recording, and walk the defined path. Hold the phone consistently throughout the recording.
3. **Export Data:** Save the collected data as a **CSV file** with columns: [timestamp, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z].

### 3.2 Step 2: Process Data with the PDR Algorithm

Use the provided `MobilePDR.py` script to process your collected data.

1. **Set Up:** Place your CSV file in the data directory.
2. **Load Your Data:** Open the Python script and modify the data loading section:

   ```python
   # In the main() function, update the file path
   df = pd.read_csv("data/your_collected_data.csv")
   ```

3. **Run the Script:** Execute the Python script. It will generate four plots:
   - Estimated 2D trajectory
   - Step detection results on filtered acceleration signal
   - Step length variation across the walk
   - Heading estimation throughout the trajectory

### 3.3 Step 3: Parameter Tuning and Performance Evaluation

Your goal is to **tune the PDR algorithm parameters** to achieve the best possible positioning accuracy.

1. **Key Tunable Parameters:**
   - **Step Detection Sensitivity:**

     ```python
     pdr.acc_threshold = 1.2     # Minimum peak height for step detection
     pdr.min_step_interval = 0.4 # Minimum time between consecutive steps
     ```

   - **Step Length Parameters:**

     ```python
     pdr.step_length = 0.65      # Average step length baseline
     ```

   - **Signal Processing:**

     ```python
     min_peak_height = 1.0       # Absolute minimum peak threshold
     window_size = int(0.5 * fs) # Window size for dynamic thresholding
     ```

2. **Performance Evaluation:**
   - **Trajectory Shape:** Does the estimated path match your actual walking pattern?
   - **Closure Error:** For closed-loop paths, measure the distance between start and end points
   - **Step Count Accuracy:** Compare detected steps with manually counted steps
   - **Distance Estimation:** Compare total estimated distance with known path length

3. **Systematic Tuning:**
   - Modify one parameter at a time and observe effects
   - Document the relationship between parameter changes and performance metrics
   - Find optimal parameter combinations for your specific dataset

---

## 4. Thinking Question

**Question 1:** Does the orientation of the smartphone during data collection affect PDR algorithm performance? Why or why not?

**Question 2:** How does heading estimation affect the performance of the PDR algorithm? What methods can be used to improve the accuracy of heading estimation?

**Question 3:** What improvements can you suggest for the `MobilePDR.py` code provided to improve the positioning accuracy of PDR? (Just give the method, no specific implementation is required)

---

## 5. Lab Report Requirement

Your lab report must include the following four sections:

1. **Analysis of Provided Code and Datasets**  
   - Run the supplied MobilePDR.py code using both `RoundTrip.csv` and `Square.csv` datasets.
   - Present and analyze the generated results (plots and statistics).

2. **Self-Collected IMU Data Experiment**  
   - Use the provided HTML IMU data collection tool to record your own walking data.
   - Describe your data collection process, including the path, phone orientation, and any relevant details.
   - Process your data with the PDR algorithm and present the results (plots and statistics).
   - Submit your raw data file together with the report.

3. **Thinking Questions**  
   - Answer the thinking questions listed above in the README.

4. **Bonus Section (Optional)**  
   - Use AI tools to create an IMU HTML data collection demo.
   - Attempt to integrate the PDR algorithm into the web page for real-time trajectory prediction and visualization.

---

## 6. References

- [SmartPDR](https://ieeexplore.ieee.org/abstract/document/6987239)
- [AAE4203 Lab Repository](https://github.com/RuijieXu0408/AAE4203Lab_Inertial-Navigation-and-PDR)
- [Basic GitHub Writing and Formatting](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)

## Contact

You can get experimental implementation methods by referring to tutorial.pdf. For detailed questions or support, please open an issue on the GitHub repository or contact TA dirrectly.
