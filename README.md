# Power Quality Analyzer

An interactive web application for detecting, classifying, and characterizing power-quality disturbances from synthetic voltage signals using digital signal-processing methods.

This project was developed as a Digital Signal Processing (DSP) course project using Python, Streamlit, PyWavelets, NumPy, and Plotly.

## Project Overview

Power-quality disturbances have different time and frequency characteristics. Voltage sags, swells, and transients occur within limited time intervals, while harmonic distortion can persist throughout an observation window.

The application therefore uses the **Stationary Wavelet Transform (SWT)** as the main time-localized analysis method and a separate **FFT-based THD analysis** for persistent harmonic distortion.

```text
Synthetic Voltage Signal
        ↓
DC Offset Removal
        ↓
Stationary Wavelet Transform (SWT)
        ↓
Feature Extraction
        ↓
Event Detection
        ↓
Event Classification
        ↓
Event Characterization
        ↓
Interactive Visualization
```

## Supported Power-Quality Events

| Condition | Description | Main analysis |
|---|---|---|
| Normal | Undisturbed sinusoidal voltage | Baseline |
| Voltage Sag | Temporary reduction in voltage magnitude | SWT-based detection |
| Voltage Swell | Temporary increase in voltage magnitude | SWT-based detection |
| Transient | Short-duration damped oscillatory disturbance | SWT-based detection |
| Harmonic Distortion | Persistent harmonic components | FFT / THD |

The voltage signal is generated mathematically with a nominal frequency of **50 Hz** and a nominal RMS voltage of **220 V**. Because the signals are synthetic, the injected event timing is known and can be used as ground truth during evaluation.

## Signal Processing Method

### Preprocessing

The generated signal is first processed to remove its DC offset:

```text
x_p[n] = x[n] - mean(x)
```

### Stationary Wavelet Transform

The application uses the **Stationary Wavelet Transform (SWT)** rather than a decimated DWT for the main event analysis.

SWT does not downsample the signal at each decomposition level. The resulting coefficients therefore remain aligned with the original time axis, which is useful for estimating event start time, end time, and duration.

Available mother wavelets:

```text
db4
db6
sym4
```

### Feature Extraction

The main localized-event feature is the short-time energy of the **Detail Level 1 (D1)** coefficient:

```text
E[n] = rolling_mean(D1[n]^2)
```

D1 is used because it is sensitive to rapid waveform changes and short-duration disturbances.

### Event Detection

Localized events are detected from the D1 energy using an adaptive threshold derived from the baseline energy.

Harmonic distortion is handled separately using the spectrum of the full signal. The system estimates THD from the fundamental component and selected harmonic components.

### Classification

After detection, the event is classified using duration, RMS level, and THD characteristics. The current rule-based classifier supports:

- Transient
- Voltage Sag
- Voltage Swell
- Harmonic Distortion
- Normal

### Characterization

The final event characterization reports:

- Event type
- Start time
- End time
- Duration
- Magnitude
- Severity

## Load and Current Simulation

The application also calculates current responses for four simplified load models:

- **R** — resistive
- **RL** — resistive-inductive
- **RC** — resistive-capacitive
- **RLC** — resistive-inductive-capacitive

The current is calculated from the same simulated voltage signal. For the RLC model, the interface also reports the calculated resonant frequency.

These load models are simplified mathematical models intended for educational and comparative analysis rather than complete representations of real electrical loads.

## Automatic SWT-Level Evaluation

Because the test signals have known event windows, the application includes an automatic comparison of SWT decomposition levels.

Two metrics are used:

**Timing Error**

```text
|detected start - ground-truth start|
+
|detected end - ground-truth end|
```

**Contrast Ratio**

The ratio between D1 energy inside the event window and D1 energy outside the event window.

The application marks the level with the smallest valid timing error as the recommended level.

## Main Features

- Synthetic 50 Hz voltage-signal generation
- Adjustable disturbance severity
- Voltage sag, swell, transient, and harmonic-distortion simulation
- Selectable SWT mother wavelet
- Adjustable decomposition level
- Interactive voltage and current waveforms
- SWT-based localized event detection
- FFT/THD-based harmonic analysis
- Event classification and characterization
- R, RL, RC, and RLC load simulation
- Automatic SWT-level evaluation
- Interactive Plotly visualizations

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core implementation |
| Streamlit | Web application interface |
| NumPy | Numerical computation |
| PyWavelets | Stationary Wavelet Transform |
| Plotly | Interactive visualization |

## Project Structure

```text
power-quality-analyzer/
│
├── power_quality_analyzer.py   # Streamlit application
├── power_quality_core.py       # Core DSP and analysis functions
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
└── .gitignore                  # Git ignore rules
```

### `power_quality_analyzer.py`

Contains the Streamlit interface, parameter controls, result presentation, and interactive visualizations.

### `power_quality_core.py`

Contains the core processing pipeline, including signal generation, load-current calculation, preprocessing, SWT decomposition, feature extraction, event detection, classification, characterization, and level evaluation.

## Installation

Clone the repository and move into the project directory:

```bash
git clone https://github.com/your-username/power-quality-analyzer.git
cd power-quality-analyzer
```

Install the required packages:

```bash
python -m pip install -r requirements.txt
```

## Running the Application

From the project directory:

```bash
python -m streamlit run power_quality_analyzer.py
```

Using `python -m streamlit` is useful when the `streamlit` executable is not available directly in the system PATH.

The command starts a local Streamlit server and provides the local application URL in the terminal.

## Streamlit Community Cloud

For deployment through Streamlit Community Cloud, use:

```text
Repository: your-username/power-quality-analyzer
Branch: main
Main file path: power_quality_analyzer.py
```

The repository root should contain:

```text
power_quality_analyzer.py
power_quality_core.py
requirements.txt
```

## Evaluation and Limitations

The project uses **synthetically generated signals**, not measurements from a physical sensor or field monitoring system.

The validation procedure includes multiple disturbance types, load models, severity levels, extreme cases, and a noise-robustness test. The experiments show that detection performance depends on signal conditions; in particular, sag and swell detection becomes less reliable under broadband noise.

This limitation is retained as part of the experimental findings of the current implementation.

Possible future work includes:

- Sensitivity analysis for R, L, and C parameters
- Systematic comparison of mother wavelets
- Evaluation across multiple noise levels
- Adaptive thresholding for noisy signals
- Testing with measured or public power-quality datasets
- Machine-learning-based classification

## References

1. J. Barros, R. I. Diego, and M. de Apráiz, “Applications of wavelets in electric power quality: Voltage events,” *Electric Power Systems Research*, vol. 88, pp. 130–136, 2012.

2. S. Madgula, V. Veeramsetty, and R. Durgam, “Signal Processing Approaches for Power Quality Disturbance Classification: A Comprehensive Review,” 2025.

3. H. A. Mohamed-Kazim and I. Abdel-Qader, “Comprehensive review of power quality disturbance detection and classification techniques,” *Computers and Electrical Engineering*, vol. 126, Art. no. 110440, 2025.

4. S. Santoso, W. M. Grady, E. J. Powers, J. Lamoree, and S. C. Bhatt, “Characterization of distribution power quality events with Fourier and wavelet transforms,” *IEEE Transactions on Power Delivery*, vol. 15, no. 1, pp. 247–254, 2000.

## Academic Context

Developed as a **Digital Signal Processing (Pengolahan Sinyal Digital)** course project.
