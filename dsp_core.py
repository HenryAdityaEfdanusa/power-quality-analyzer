"""
dsp_core.py
------------------------------------------------------------------
Core DSP pipeline for DWT-based Power Quality Event Detection and
Classification.

Pipeline:
    Signal Generation -> Preprocessing -> DWT (SWT) -> Feature
    Extraction -> Detection -> Classification -> Characterization

Notes on the wavelet transform
-------------------------------
This module uses the Stationary (undecimated) Wavelet Transform,
`pywt.swt`, rather than the plain `pywt.wavedec`. A standard DWT
downsamples at every level, so detail coefficients at level j no
longer line up sample-for-sample with the original time axis --
that makes it awkward to report an event's start/end time directly
from the coefficients. SWT skips the downsampling step, so every
detail/approximation array is the same length as the input signal
and stays aligned in time, which is what "characterization" (start
time, end time, duration) needs.

`pywt.swt(..., trim_approx=False)` returns coefficients ordered like
`wavedec`: [(cA_L, cD_L), ..., (cA_1, cD_1)] -- i.e. the LAST tuple
in the list is level 1, the finest scale. Level 1 has the smallest
filter support and reacts fastest/sharpest to a local discontinuity
(a sag/swell edge, a transient spike), which is why it is used here
as the main feature for event detection.
"""

import numpy as np
import pywt

NOMINAL_FREQ = 50.0        # Hz
NOMINAL_RMS_VOLTAGE = 220.0
NOMINAL_AMPLITUDE = NOMINAL_RMS_VOLTAGE * np.sqrt(2.0)  # V peak
DEFAULT_RESISTANCE = 10.0  # ohm, about 22 A RMS at nominal voltage
DEFAULT_INDUCTANCE = 0.03  # H, about 22 A RMS steady-state for the RL load
DEFAULT_CAPACITANCE = 100e-6  # F, 100 uF for parallel RC/RLC loads


# ---------------------------------------------------------------------------
# 1. SIGNAL GENERATION
# ---------------------------------------------------------------------------

def generate_signal(
    disturbance="normal",
    fs=10_000,
    duration=0.5,
    f0=NOMINAL_FREQ,
    amplitude=NOMINAL_AMPLITUDE,
    event_start=0.20,
    event_duration=0.10,
    severity=0.5,
    noise_level=0.0,
    seed=None,
):
    """
    Generate a synthetic voltage signal v[n] = A*sin(2*pi*f0*t) with an
    optional power-quality disturbance injected starting at `event_start`.

    disturbance : "normal" | "sag" | "swell" | "transient" | "harmonic"
    severity    : 0..1, meaning depends on disturbance type
    Returns (t, v, ground_truth) where ground_truth records the type
    and [start, end] window actually injected, for evaluation purposes.
    """
    rng = np.random.default_rng(seed)
    n = int(fs * duration)
    t = np.arange(n) / fs
    v = amplitude * np.sin(2 * np.pi * f0 * t)

    ground_truth = {"type": "Normal", "start": None, "end": None}
    t1 = event_start
    t2 = min(event_start + event_duration, duration)
    mask = (t >= t1) & (t < t2)

    if disturbance == "sag":
        depth = 0.15 + 0.6 * severity              # 0.15 - 0.75 pu drop
        v[mask] *= (1 - depth)
        ground_truth = {"type": "Voltage Sag", "start": t1, "end": t2}

    elif disturbance == "swell":
        gain = 0.15 + 0.55 * severity               # 1.15 - 1.70 pu
        v[mask] *= (1 + gain)
        ground_truth = {"type": "Voltage Swell", "start": t1, "end": t2}

    elif disturbance == "transient":
        t2 = min(t1 + 0.02 + 0.02 * severity, duration)   # 20-40 ms burst
        mask = (t >= t1) & (t < t2)
        tau = t[mask] - t1
        osc_freq = 800 + 2500 * severity            # 0.8 - 3.3 kHz
        burst = amplitude * (0.3 + 0.9 * severity) * np.exp(-tau / 0.006) * np.sin(2 * np.pi * osc_freq * tau)
        v[mask] += burst
        ground_truth = {"type": "Transient", "start": t1, "end": t2}

    elif disturbance == "harmonic":
        thd = 0.15 + 0.35 * severity
        v += thd * amplitude * 0.6 * np.sin(2 * np.pi * 3 * f0 * t)
        v += thd * amplitude * 0.3 * np.sin(2 * np.pi * 5 * f0 * t)
        v += thd * amplitude * 0.1 * np.sin(2 * np.pi * 7 * f0 * t)
        ground_truth = {"type": "Harmonic Distortion", "start": 0.0, "end": duration}

    if noise_level > 0:
        v = v + rng.normal(0, noise_level, size=n)

    return t, v, ground_truth


def generate_current(
    voltage,
    fs,
    load_type="R",
    resistance=DEFAULT_RESISTANCE,
    inductance=DEFAULT_INDUCTANCE,
    capacitance=DEFAULT_CAPACITANCE,
):
    """Calculate current for R, series RL, parallel RC, or parallel RLC loads.

    R uses the instantaneous Ohm-law response, ``i[n] = v[n] / R``, so it
    has no electrical state and no startup transient. RL uses backward Euler
    for ``L * di/dt + R * i = v`` and starts with ``i[0] = 0``.

    RC and RLC are parallel loads, so every branch sees the known source
    voltage directly. Their total current is the sum of the R, L, and C
    branch currents; the capacitor uses a backward difference and the
    inductor uses an explicit forward-Euler accumulation.
    """
    voltage = np.asarray(voltage, dtype=float)
    if resistance <= 0:
        raise ValueError("resistance must be greater than zero")
    if load_type not in {"R", "RL", "RC", "RLC"}:
        raise ValueError("load_type must be 'R', 'RL', 'RC', or 'RLC'")

    resistive_current = voltage / resistance
    if load_type == "R":
        return resistive_current

    dt = 1.0 / fs
    if load_type == "RL":
        if inductance <= 0:
            raise ValueError("inductance must be greater than zero for an RL load")

        current = np.zeros_like(voltage)
        alpha = inductance / dt + resistance
        for index in range(1, len(voltage)):
            current[index] = (
                voltage[index] + (inductance / dt) * current[index - 1]
            ) / alpha
        return current

    if capacitance <= 0:
        raise ValueError("capacitance must be greater than zero for RC/RLC loads")

    capacitive_current = np.zeros_like(voltage)
    capacitive_current[1:] = capacitance * np.diff(voltage) / dt
    if load_type == "RC":
        return resistive_current + capacitive_current

    if inductance <= 0:
        raise ValueError("inductance must be greater than zero for an RLC load")

    inductive_current = np.zeros_like(voltage)
    for index in range(1, len(voltage)):
        inductive_current[index] = (
            inductive_current[index - 1] + voltage[index] * dt / inductance
        )
    return resistive_current + inductive_current + capacitive_current


# ---------------------------------------------------------------------------
# 2. PREPROCESSING
# ---------------------------------------------------------------------------

def preprocess(v):
    """Remove DC offset: x_p[n] = x[n] - mean(x)."""
    return v - np.mean(v)


# ---------------------------------------------------------------------------
# 3. DWT  (Stationary Wavelet Transform)
# ---------------------------------------------------------------------------

def dwt_decompose(v, wavelet="db4", level=4):
    """
    Undecimated wavelet decomposition, time-aligned with the input.
    `pywt.swt` requires len(v) to be a multiple of 2**level, so the
    signal is edge-padded internally and cropped back afterwards.

    Returns a list ordered [ (cA_L, cD_L), ..., (cA_1, cD_1) ] --
    index -1 is level 1 (finest scale).
    """
    n = len(v)
    pad = (2 ** level - n % (2 ** level)) % (2 ** level)
    v_pad = np.pad(v, (0, pad), mode="edge")
    coeffs = pywt.swt(v_pad, wavelet=wavelet, level=level, trim_approx=False)
    return [(cA[:n], cD[:n]) for cA, cD in coeffs]


def levels_by_number(coeffs):
    """Re-key the coefficient list as {1: cD_1 (finest), ..., L: cD_L (coarsest)}."""
    L = len(coeffs)
    return {j: coeffs[L - j][1] for j in range(1, L + 1)}


# ---------------------------------------------------------------------------
# 4. FEATURE EXTRACTION
# ---------------------------------------------------------------------------

def rolling_energy(x, win):
    """Centred rolling mean of squares (a short-time energy estimate)."""
    x2 = x ** 2
    kernel = np.ones(win) / win
    return np.convolve(x2, kernel, mode="same")


def extract_features(coeffs, fs, win_ms=4):
    """
    Level-1 (finest) detail energy, in a short rolling window, is the
    feature used for detection -- it responds sharply to local edges
    and transients while staying low on the smooth steady-state wave.
    """
    _, d1 = coeffs[-1]
    win = max(1, int(fs * win_ms / 1000))
    energy = rolling_energy(d1, win)
    return {"d1": d1, "energy": energy, "win_samples": win}


# ---------------------------------------------------------------------------
# 5. DETECTION
# ---------------------------------------------------------------------------

def detect_event(features, k=2.5, baseline_frac=0.5, edge_margin=150):
    """
    E[n] > T  => event, where T = k * (a mid quantile of E, used as an
    estimate of the steady-state / noise-floor energy level).

    `edge_margin` samples at both ends of the record are excluded from
    consideration. The SWT is computed on an edge-padded signal, and the
    boundary padding itself introduces a small filter-transient artifact
    into the finest detail level near t=0 and t=duration; without this
    margin that artifact can be mistaken for a real disturbance.
    """
    energy = features["energy"]
    n = len(energy)
    margin = min(edge_margin, n // 4)
    inner = slice(margin, n - margin) if margin > 0 else slice(0, n)

    floor = np.quantile(energy[inner], baseline_frac)
    threshold = max(floor * k, 1e-12)

    is_event = np.zeros(n, dtype=bool)
    is_event[inner] = energy[inner] > threshold

    if not np.any(is_event):
        return {"detected": False, "mask": is_event, "threshold": threshold}

    idx = np.where(is_event)[0]
    return {
        "detected": True,
        "mask": is_event,
        "threshold": threshold,
        "start_idx": int(idx[0]),
        "end_idx": int(idx[-1]),
    }


# ---------------------------------------------------------------------------
# 6. CLASSIFICATION  (rule-based, IEEE-1159-inspired thresholds)
# ---------------------------------------------------------------------------

def estimate_thd(v, fs, f0=NOMINAL_FREQ, harmonic_orders=(3, 5, 7)):
    """Estimate THD from the fundamental and selected harmonic FFT bins."""
    spectrum = np.abs(np.fft.rfft(v))
    frequencies = np.fft.rfftfreq(len(v), d=1.0 / fs)

    def bin_amplitude(frequency):
        index = int(np.argmin(np.abs(frequencies - frequency)))
        return spectrum[index]

    fundamental = bin_amplitude(f0)
    if fundamental <= 1e-12:
        return 0.0

    harmonic_energy = sum(bin_amplitude(order * f0) ** 2 for order in harmonic_orders)
    return float(np.sqrt(harmonic_energy) / fundamental)


def classify_event(
    t,
    v,
    detection,
    fs,
    f0=NOMINAL_FREQ,
    amplitude=NOMINAL_AMPLITUDE,
    harmonic_threshold=0.05,
):
    # Harmonics persist through the record, so they need a full-signal FFT
    # detector independent of the localized D1 event mask.
    thd = estimate_thd(v, fs, f0=f0)
    if thd > harmonic_threshold:
        return {"type": "Harmonic Distortion", "thd": thd}

    if not detection["detected"]:
        return {"type": "Normal"}

    i0, i1 = detection["start_idx"], detection["end_idx"]
    seg = v[i0:i1 + 1]
    if len(seg) == 0:
        return {"type": "Normal"}

    duration = (i1 - i0) / fs
    n_cycles = duration * f0
    rms_pu = np.sqrt(np.mean(seg ** 2)) / (amplitude / np.sqrt(2))

    if n_cycles < 2.5:
        ev_type = "Transient"
    elif rms_pu < 0.9:
        ev_type = "Voltage Sag"
    elif rms_pu > 1.1:
        ev_type = "Voltage Swell"
    else:
        ev_type = "Normal"

    return {"type": ev_type, "rms_pu": float(rms_pu), "duration": duration}


# ---------------------------------------------------------------------------
# 7. CHARACTERIZATION
# ---------------------------------------------------------------------------

def _severity_label(ev_type, rms_pu):
    if ev_type == "Voltage Sag":
        if rms_pu < 0.5:
            return "Severe"
        if rms_pu < 0.8:
            return "Moderate"
        return "Mild"
    if ev_type == "Voltage Swell":
        if rms_pu > 1.5:
            return "Severe"
        if rms_pu > 1.2:
            return "Moderate"
        return "Mild"
    if ev_type == "Transient":
        return "—"
    if ev_type == "Harmonic Distortion":
        return "—"
    return "—"


def characterize_event(t, v, detection, classification, fs):
    ev_type = classification["type"]
    if ev_type == "Harmonic Distortion" and not detection["detected"]:
        thd = classification.get("thd", 0.0)
        if thd < 0.10:
            severity = "Mild"
        elif thd <= 0.20:
            severity = "Moderate"
        else:
            severity = "Severe"

        return {
            "type": ev_type,
            "start": float(t[0]),
            "end": float(t[-1]),
            "duration_ms": (t[-1] - t[0]) * 1000.0,
            "magnitude_pu": None,
            "severity": severity,
        }

    if not detection["detected"]:
        return {
            "type": "Normal", "start": None, "end": None,
            "duration_ms": None, "magnitude_pu": None, "severity": "—",
        }

    i0, i1 = detection["start_idx"], detection["end_idx"]
    seg = v[i0:i1 + 1]
    magnitude = float(np.min(np.abs(seg))) if ev_type == "Voltage Sag" else float(np.max(np.abs(seg)))
    rms_pu = classification.get("rms_pu", magnitude)

    return {
        "type": ev_type,
        "start": float(t[i0]),
        "end": float(t[i1]),
        "duration_ms": (t[i1] - t[i0]) * 1000.0,
        "magnitude_pu": magnitude,
        "severity": _severity_label(ev_type, rms_pu),
    }


# ---------------------------------------------------------------------------
# FULL PIPELINE
# ---------------------------------------------------------------------------

def run_pipeline(t, v_raw, fs, wavelet="db4", level=4, k=6.0):
    v = preprocess(v_raw)
    coeffs = dwt_decompose(v, wavelet=wavelet, level=level)
    features = extract_features(coeffs, fs)
    detection = detect_event(features, k=k)
    classification = classify_event(t, v_raw, detection, fs)
    characterization = characterize_event(t, v_raw, detection, classification, fs)
    return {
        "v_clean": v,
        "coeffs": coeffs,
        "levels": levels_by_number(coeffs),
        "features": features,
        "detection": detection,
        "classification": classification,
        "characterization": characterization,
    }


def evaluate_levels(t, v_raw, fs, ground_truth, wavelet="db4", max_level=6, k=6.0):
    """Compare SWT levels against an injected event's timing and D1 contrast."""
    if max_level < 1:
        raise ValueError("max_level must be at least 1")

    event_start = ground_truth.get("start")
    event_end = ground_truth.get("end")
    has_event_window = event_start is not None and event_end is not None
    t = np.asarray(t)
    event_mask = (t >= event_start) & (t <= event_end) if has_event_window else None
    results = []

    for candidate_level in range(1, max_level + 1):
        result = run_pipeline(t, v_raw, fs, wavelet=wavelet, level=candidate_level, k=k)
        characterization = result["characterization"]
        detected_start = characterization["start"]
        detected_end = characterization["end"]

        if (
            has_event_window
            and characterization["type"] != "Normal"
            and detected_start is not None
            and detected_end is not None
        ):
            timing_error_ms = 1000.0 * (
                abs(detected_start - event_start) + abs(detected_end - event_end)
            )
        else:
            timing_error_ms = float("nan")

        detail_level_1 = result["features"]["d1"]
        if event_mask is None or not np.any(event_mask) or np.all(event_mask):
            contrast_ratio = float("nan")
        else:
            event_energy = np.mean(detail_level_1[event_mask] ** 2)
            background_energy = np.mean(detail_level_1[~event_mask] ** 2)
            contrast_ratio = (
                float(event_energy / background_energy)
                if background_energy > np.finfo(float).eps
                else float("nan")
            )

        results.append(
            {
                "level": candidate_level,
                "timing_error_ms": float(timing_error_ms),
                "contrast_ratio": contrast_ratio,
                "detected_type": characterization["type"],
            }
        )

    return results
