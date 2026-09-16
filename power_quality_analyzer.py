import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

from power_quality_core import (
    DEFAULT_CAPACITANCE,
    DEFAULT_INDUCTANCE,
    DEFAULT_RESISTANCE,
    evaluate_levels,
    generate_current,
    generate_signal,
    levels_by_number,
    run_pipeline,
)


st.set_page_config(page_title="Power Quality Analyzer", layout="wide")
st.session_state.setdefault("has_analyzed", False)
st.title("Power Quality Analyzer")
st.markdown("Deteksi gangguan kualitas daya berbasis Stationary Wavelet Transform")

EVENTS = {
    "Normal": "normal",
    "Voltage Sag": "sag",
    "Voltage Swell": "swell",
    "Transient": "transient",
    "Harmonic Distortion": "harmonic",
}

with st.sidebar:
    st.header("Pengaturan Parameter")
    event_label = st.selectbox("Jenis sinyal / gangguan", list(EVENTS))
    disturbance_severity = st.slider(
        "Severity Gangguan",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05,
    )
    load_type = st.selectbox("Jenis beban", ["R", "RL", "RC", "RLC"])
    resistance = st.slider(
        "Resistance (ohm)",
        min_value=5.0,
        max_value=50.0,
        value=DEFAULT_RESISTANCE,
        step=1.0,
    )
    if "L" in load_type:
        inductance = st.slider(
            "Inductance (H)",
            min_value=0.01,
            max_value=0.10,
            value=DEFAULT_INDUCTANCE,
            step=0.01,
        )
    else:
        inductance = DEFAULT_INDUCTANCE
    if "C" in load_type:
        capacitance_microfarads = st.slider(
            "Capacitance (µF)",
            min_value=10.0,
            max_value=500.0,
            value=DEFAULT_CAPACITANCE * 1e6,
            step=10.0,
        )
        capacitance = capacitance_microfarads * 1e-6
    else:
        capacitance = DEFAULT_CAPACITANCE
    wavelet_type = st.selectbox("Mother wavelet", ["db4", "db6", "sym4"])
    level = st.slider("Level dekomposisi", 1, 6, 3)
    selected_level = st.selectbox(
        "Tampilkan Detail Level",
        options=list(range(1, level + 1)),
        index=0,
    )
    auto_level_search = st.checkbox(
        "Cari Level Terbaik (Auto)",
        help="Bandingkan seluruh level SWT 1 hingga 6 setelah Analisis Sinyal dijalankan.",
    )
    analyze_btn = st.button("Analisis Sinyal", width="stretch")

if analyze_btn:
    st.session_state["has_analyzed"] = True

fs = 10_000
t, voltage, ground_truth = generate_signal(
    EVENTS[event_label],
    fs=fs,
    severity=disturbance_severity,
)
current_r = generate_current(voltage, fs, "R", resistance)
current = generate_current(
    voltage,
    fs,
    load_type,
    resistance,
    inductance,
    capacitance,
)

if st.session_state["has_analyzed"]:
    result = run_pipeline(t, voltage, fs, wavelet=wavelet_type, level=level)
    characterization = result["characterization"]
    classification = result["classification"]
    detection = result["detection"]
    status = characterization["type"]

    st.subheader("Hasil Diagnosis")
    if detection["detected"]:
        st.success(f"Terdeteksi: {status}")
    else:
        st.info(status)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Jenis gangguan", characterization["type"])
    col2.metric(
        "Waktu mulai",
        "-" if characterization["start"] is None else f"{characterization['start']:.4f} s",
    )
    col3.metric(
        "Durasi",
        "-" if characterization["duration_ms"] is None else f"{characterization['duration_ms']:.1f} ms",
    )
    col4.metric("Severity", characterization["severity"])

    rms_text = f"RMS event: {classification['rms_pu']:.3f} pu | " if "rms_pu" in classification else ""
    load_parameters = f"R = {resistance:.1f} ohm"
    if "L" in load_type:
        load_parameters += f" | L = {inductance:.2f} H"
    if "C" in load_type:
        load_parameters += f" | C = {capacitance * 1e6:.0f} µF"
    if load_type == "RLC":
        resonant_frequency = 1.0 / (2.0 * np.pi * np.sqrt(inductance * capacitance))
        load_parameters += (
            f" | f_res = {resonant_frequency:.1f} Hz "
            "(bandingkan harmonik: 150/250/350 Hz)"
        )
    st.caption(f"{rms_text}Beban: {load_type} | {load_parameters}")

    st.subheader("1. Tegangan dan Arus Beban")
    waveform = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08)
    waveform.add_trace(go.Scatter(x=t, y=voltage, name="Voltage", line=dict(color="royalblue")), row=1, col=1)
    waveform.add_trace(go.Scatter(x=t, y=current, name="Current", line=dict(color="firebrick")), row=2, col=1)
    if detection["detected"]:
        waveform.add_vrect(
            x0=characterization["start"],
            x1=characterization["end"],
            fillcolor="red",
            opacity=0.15,
            line_width=0,
        )
    waveform.update_yaxes(title_text="Voltage (V)", nticks=8, row=1, col=1)
    waveform.update_yaxes(title_text="Current (A)", nticks=8, row=2, col=1)
    waveform.update_xaxes(title_text="Waktu (s)", nticks=10, row=1, col=1)
    waveform.update_xaxes(title_text="Waktu (s)", nticks=10, row=2, col=1)
    waveform.update_layout(height=500, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(waveform, width="stretch")

    show_normalized = st.checkbox("Tampilkan bentuk gelombang ternormalisasi")
    if show_normalized:
        voltage_norm = voltage / np.max(np.abs(voltage))
        current_norm = current / np.max(np.abs(current))
        normalized_waveform = go.Figure()
        normalized_waveform.add_trace(
            go.Scatter(
                x=t,
                y=voltage_norm,
                name="Voltage ternormalisasi",
                line=dict(color="royalblue"),
            )
        )
        normalized_waveform.add_trace(
            go.Scatter(
                x=t,
                y=current_norm,
                name="Current ternormalisasi",
                line=dict(color="firebrick"),
            )
        )
        if detection["detected"]:
            normalized_waveform.add_vrect(
                x0=characterization["start"],
                x1=characterization["end"],
                fillcolor="red",
                opacity=0.15,
                line_width=0,
            )
        normalized_waveform.update_layout(
            height=360,
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(title="Waktu (s)", nticks=10),
            yaxis=dict(title="Amplitudo Ternormalisasi", nticks=8),
        )
        st.plotly_chart(normalized_waveform, width="stretch")
    st.caption(f"Parameter beban aktif: {load_parameters}")

    st.subheader("2. Perbandingan Arus: Beban Aktif vs Baseline R")
    st.caption(
        "Arus beban aktif dibandingkan dengan baseline R dari sinyal tegangan yang sama."
    )
    current_comparison = go.Figure()
    current_comparison.add_trace(
        go.Scatter(
            x=t,
            y=current,
            name=f"Arus beban aktif ({load_type})",
            line=dict(color="firebrick"),
        )
    )
    current_comparison.add_trace(
        go.Scatter(
            x=t,
            y=current_r,
            name="Baseline arus R",
            line=dict(color="darkgreen"),
        )
    )
    if detection["detected"]:
        current_comparison.add_vrect(
            x0=characterization["start"],
            x1=characterization["end"],
            fillcolor="red",
            opacity=0.15,
            line_width=0,
        )
    current_comparison.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis=dict(title="Waktu (s)", nticks=10),
        yaxis=dict(title="Arus (A)", nticks=8),
    )
    st.plotly_chart(current_comparison, width="stretch")
    st.caption(
        f"RMS arus aktif ({load_type}): {(current ** 2).mean() ** 0.5:.2f} A | "
        f"RMS baseline R: {(current_r ** 2).mean() ** 0.5:.2f} A."
    )

    st.subheader("3. Koefisien SWT")
    st.caption(f"Mother wavelet: {wavelet_type} | Level dekomposisi: {level}")
    approximation = result["coeffs"][0][0]
    detail = levels_by_number(result["coeffs"])[selected_level]
    coefficients = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("Approximation", f"Detail Level {selected_level}"),
    )
    coefficients.add_trace(go.Scatter(x=t, y=approximation, name="Approximation"), row=1, col=1)
    coefficients.add_trace(
        go.Scatter(x=t, y=detail, name=f"Detail Level {selected_level}"),
        row=2,
        col=1,
    )
    coefficients.update_xaxes(nticks=10)
    coefficients.update_xaxes(title_text="Waktu (s)", nticks=10, row=2, col=1)
    coefficients.update_layout(height=500, margin=dict(l=0, r=0, t=45, b=0), showlegend=False)
    st.plotly_chart(coefficients, width="stretch")

    if auto_level_search:
        auto_level_results = evaluate_levels(
            t,
            voltage,
            fs,
            ground_truth,
            wavelet=wavelet_type,
            max_level=6,
        )
        valid_timing = [
            row for row in auto_level_results if np.isfinite(row["timing_error_ms"])
        ]
        recommended = min(valid_timing, key=lambda row: row["timing_error_ms"], default=None)
        recommended_level = recommended["level"] if recommended else None

        st.subheader("4. Pencarian Level SWT Otomatis")
        if recommended:
            st.success(
                f"Level Rekomendasi: {recommended_level} "
                f"(timing error {recommended['timing_error_ms']:.2f} ms)"
            )
        else:
            st.warning("Tidak ada timing error yang dapat dihitung untuk sinyal ini.")

        labels = [f"Level {row['level']}" for row in auto_level_results]
        colors = [
            "seagreen" if row["level"] == recommended_level else "steelblue"
            for row in auto_level_results
        ]
        level_comparison = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=("Timing error (ms)", "Contrast ratio energi D1"),
        )
        level_comparison.add_trace(
            go.Bar(
                x=labels,
                y=[
                    row["timing_error_ms"]
                    if np.isfinite(row["timing_error_ms"])
                    else None
                    for row in auto_level_results
                ],
                marker_color=colors,
                name="Timing error",
            ),
            row=1,
            col=1,
        )
        level_comparison.add_trace(
            go.Bar(
                x=labels,
                y=[
                    row["contrast_ratio"]
                    if np.isfinite(row["contrast_ratio"])
                    else None
                    for row in auto_level_results
                ],
                marker_color=colors,
                name="Contrast ratio",
            ),
            row=1,
            col=2,
        )
        level_comparison.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=45, b=0),
            showlegend=False,
        )
        level_comparison.update_xaxes(nticks=10)
        st.plotly_chart(level_comparison, width="stretch")

        table_rows = [
            {
                "Level": row["level"],
                "Timing Error (ms)": (
                    f"{row['timing_error_ms']:.2f}"
                    if np.isfinite(row["timing_error_ms"])
                    else "—"
                ),
                "Contrast Ratio": (
                    f"{row['contrast_ratio']:.3f}"
                    if np.isfinite(row["contrast_ratio"])
                    else "—"
                ),
                "Tipe Terdeteksi": row["detected_type"],
                "Status": (
                    "Level Rekomendasi" if row["level"] == recommended_level else ""
                ),
            }
            for row in auto_level_results
        ]
        st.dataframe(table_rows, hide_index=True, width="stretch")
        st.caption(
            "Timing error = |awal terdeteksi − awal ground truth| + "
            "|akhir terdeteksi − akhir ground truth|. Contrast ratio memakai "
            "rata-rata energi cD1² di dalam versus di luar window event."
        )
else:
    st.info("Pilih parameter di sidebar, lalu klik Analisis Sinyal untuk memulai.")
