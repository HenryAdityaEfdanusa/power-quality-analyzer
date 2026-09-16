# Power Quality Analyzer

An interactive web application for analyzing power-quality disturbances from synthetic voltage signals. The application uses the **Stationary Wavelet Transform (SWT)** for time-localized event detection and combines it with FFT-based harmonic analysis for persistent distortion.

## Overview

Power-quality disturbances are not all visible in the same way. Voltage sags, swells, and transients are localized in time, while harmonic distortion is present throughout the signal. This project therefore uses two complementary analysis paths:

- **SWT-based analysis** for localized disturbances
- **FFT/THD analysis** for harmonic distortion

The application presents the results through an interactive Streamlit interface, including voltage/current waveforms, wavelet coefficients, event characteristics, and automatic SWT-level evaluation.

## Detected Events

The current implementation supports five operating conditions:

| Event | Analysis approach |
|---|---|
| Normal | Baseline condition |
| Voltage Sag | SWT detail-energy detection |
| Voltage Swell | SWT detail-energy detection |
| Transient | SWT detail-energy detection |
| Harmonic Distortion | FFT-based THD detection |

The disturbance signals are generated mathematically rather than collected from a physical measurement system. This makes the event timing and disturbance parameters available as ground truth for evaluation.

## Analysis Pipeline

```text
Synthetic Voltage Signal
          │
          ▼
   DC Offset Removal
          │
          ▼
  Stationary Wavelet
      Transform
          │
          ▼
   Feature Extraction
       (D1 Energy)
          │
          ▼
   Event Detection
          │
          ├───────────────► FFT / THD
          │
          ▼
     Classification
          │
          ▼
    Characterization
          │
          ▼
 Interactive Visualization
```

For localized events, the finest-scale detail coefficient (**D1**) is processed using a short rolling-energy window. The resulting energy is compared with an adaptive threshold to identify abnormal regions.

Harmonic distortion is evaluated separately from the full signal spectrum using the fundamental component and the 3rd, 5th, and 7th harmonics.

## Load Models

The application also calculates the corresponding current response for four simplified load models:

- **R** — resistive
- **RL** — resistive-inductive
- **RC** — resistive-capacitive
- **RLC** — resistive-inductive-capacitive

These models allow the effect of the selected voltage waveform to be viewed from both voltage and current perspectives. For the RLC case, the interface also reports the calculated resonant frequency.

## Main Features

- Synthetic 50 Hz voltage-signal generation
- Adjustable disturbance severity
- Voltage sag, swell, transient, and harmonic-distortion simulation
- SWT analysis with selectable mother wavelets (`db4`, `db6`, `sym4`)
- Configurable decomposition level
- Automatic SWT-level comparison
- Event start time and duration estimation
- Severity characterization
- Interactive voltage/current plots with Plotly
- R, RL, RC, and RLC load simulation
- FFT-based THD estimation for harmonic distortion

## Technology

| Component | Role |
|---|---|
| Python | Core implementation |
| Streamlit | Interactive web interface |
| NumPy | Numerical computation |
| PyWavelets | Stationary Wavelet Transform |
| Plotly | Interactive visualization |

## Project Structure

```text
power-quality-analyzer/
├── dsp.py
├── dsp_core.py
├── requirements.txt
├── README.md
└── .gitignore
```

### `dsp.py`

Streamlit application layer. It handles user inputs, visualization, result presentation, and application flow.

### `dsp_core.py`

Core signal-processing module containing signal generation, load-current calculation, preprocessing, SWT decomposition, feature extraction, detection, classification, characterization, and level evaluation.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/HenryAdityaEfdanusa/power-quality-analyzer.git
cd power-quality-analyzer
```

### 2. Install the dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
streamlit run dsp.py
```

The application will then be available through the local Streamlit server.

## Streamlit Deployment

The application can be deployed using **Streamlit Community Cloud**.

Use:

```text
Main file path: dsp.py
```

The repository root should contain `dsp.py`, `dsp_core.py`, and `requirements.txt`.

## Evaluation Notes

The application includes an automatic SWT-level evaluation mode because the synthetic test signals have known event windows. Two metrics are used:

- **Timing error** — difference between detected and known event boundaries
- **Contrast ratio** — event-region D1 energy relative to the background

The current implementation is intended as an educational and experimental signal-processing project. It does not represent a complete field-ready power-quality monitoring system.

In particular, the validation performed for this project uses synthetic signals, and performance under noise is not uniform across all event types. This limitation is retained deliberately because it is part of the experimental findings rather than being hidden behind an accuracy-only summary.

## References

1. J. Barros, R. I. Diego, and M. de Apráiz, “Applications of wavelets in electric power quality: Voltage events,” *Electric Power Systems Research*, vol. 88, pp. 130–136, 2012. https://doi.org/10.1016/j.epsr.2012.02.009

2. S. N. R. Madgula, V. Veeramsetty, and R. Durgam, “Signal Processing Approaches for Power Quality Disturbance Classification: A Comprehensive Review,” *Results in Engineering*, vol. 25, 104569, 2025. https://doi.org/10.1016/j.rineng.2025.104569

3. A. A. Memon, M. A. Koondhar, S. F. Al-Gahtani, Z. M. S. Elbarbary, and Z. M. Alaas, “Comprehensive review of power quality disturbance detection and classification techniques,” *Computers and Electrical Engineering*, vol. 126, 110512, 2025. https://doi.org/10.1016/j.compeleceng.2025.110512

4. S. Santoso, W. M. Grady, E. J. Powers, J. Lamoree, and S. C. Bhatt, “Characterization of distribution power quality events with Fourier and wavelet transforms,” *IEEE Transactions on Power Delivery*, vol. 15, no. 1, pp. 247–254, 2000. https://doi.org/10.1109/61.847259

## Academic Project

Developed as a **Digital Signal Processing (Pengolahan Sinyal Digital)** course project.
