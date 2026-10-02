"""
Image Entropy Analyzer
----------------------

Information Theory mini-project:
Analysis of digital images using Shannon entropy,
pixel distributions, redundancy, and colour-channel entropy.
"""

from __future__ import annotations

from textwrap import dedent

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from entropy import analyze_image
from image_utils import (
    SUPPORTED_FORMATS,
    convert_to_grayscale,
    format_file_size,
    grayscale_array,
    load_image,
    rgb_channel_arrays,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Image Entropy Analyzer",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.html(
    dedent(
        """
        <style>

        /* ====================================================
           GLOBAL
           ==================================================== */

        .stApp {
            background: #ffffff !important;
            color: #18221c !important;
        }

        .main {
            padding-top: 1.8rem;
            padding-bottom: 4rem;
        }

        .block-container {
            max-width: 1250px;
            padding-left: 3.3rem;
            padding-right: 3.3rem;
        }

        html,
        body {
            background: #ffffff !important;
        }

        /* ====================================================
           HIDE STREAMLIT DEFAULT CHROME
           ==================================================== */

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        header {
            background: transparent !important;
        }

        [data-testid="stAppDeployButton"] {
            display: none !important;
        }

        /* ====================================================
           HEADER
           ==================================================== */

        .project-label {
            color: #6d9078;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 0.65rem;
        }

        .project-title {
            color: #17221b;
            font-size: 3.25rem;
            font-weight: 700;
            letter-spacing: -0.045em;
            line-height: 1;
            margin: 0;
        }

        .project-subtitle {
            color: #59675f;
            font-size: 1.06rem;
            font-weight: 400;
            line-height: 1.55;
            margin-top: 0.85rem;
            margin-bottom: 0.35rem;
        }

        .project-how {
            color: #718078;
            font-size: 0.92rem;
            font-weight: 500;
            line-height: 1.5;
            margin-top: 0.15rem;
            margin-bottom: 2.4rem;
        }

        .project-how span {
            color: #54745c;
            font-weight: 700;
        }

        /* ====================================================
           TABS
           ==================================================== */

        .stTabs [data-baseweb="tab-list"] {
            gap: 2.4rem;
            border-bottom: 1px solid #d2dfd6;
            background: #ffffff !important;
        }

        .stTabs [data-baseweb="tab"] {
            background: transparent !important;
            color: #707b74 !important;
            border-radius: 0 !important;
            font-size: 0.98rem !important;
            font-weight: 600 !important;
            padding: 0.8rem 0 0.95rem 0 !important;
        }

        .stTabs [aria-selected="true"] {
            color: #35563e !important;
            font-weight: 700 !important;
        }

        .stTabs [data-baseweb="tab-highlight"] {
            background: #73967d !important;
            height: 2px !important;
        }

        /* ====================================================
           HEADINGS
           ==================================================== */

        .section-title {
            color: #18231c;
            font-size: 1.28rem;
            font-weight: 700;
            letter-spacing: -0.015em;
            margin-top: 1.9rem;
            margin-bottom: 0.75rem;
        }

        .small-label {
            color: #708077;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.13em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }

        .body-copy {
            color: #5d6a62;
            font-size: 0.98rem;
            line-height: 1.65;
        }

        .rule {
            width: 100%;
            height: 1px;
            background: #d4e0d8;
            margin: 1.7rem 0;
        }

        /* ====================================================
           FILE UPLOADER
           ==================================================== */

        [data-testid="stFileUploader"] {
            margin-top: 0.4rem;
        }

        [data-testid="stFileUploader"] label {
            color: #18221c !important;
            font-size: 1rem !important;
            font-weight: 700 !important;
        }

        [data-testid="stFileUploaderDropzone"] {
            min-height: 150px !important;
            background: #f5f9f6 !important;
            border: 1px solid #bfd1c4 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }

        [data-testid="stFileUploaderDropzone"]:hover {
            background: #f0f6f1 !important;
            border-color: #7d9e85 !important;
        }

        [data-testid="stFileUploaderDropzoneInstructions"],
        [data-testid="stFileUploaderDropzoneInstructions"] div {
            color: #58675e !important;
            font-size: 0.95rem !important;
        }

        [data-testid="stFileUploaderDropzone"] button {
            background: #e7f0e9 !important;
            color: #31523b !important;
            border: 1px solid #9db8a3 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            font-weight: 700 !important;
        }

        [data-testid="stFileUploaderDropzone"] button:hover {
            background: #dceadf !important;
            border-color: #75947d !important;
        }

        /* ====================================================
           METRICS
           ==================================================== */

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            width: 100%;
            border-top: 2px solid #bfd1c4;
            border-bottom: 1px solid #d7e1da;
        }

        .metric-item {
            padding: 1rem 1.25rem 1.05rem 0;
            margin-right: 1.25rem;
            border-right: 1px solid #d7e1da;
        }

        .metric-item:last-child {
            border-right: none;
            margin-right: 0;
        }

        .metric-number {
            color: #365f41;
            font-size: 1.85rem;
            font-weight: 700;
            line-height: 1.05;
            letter-spacing: -0.03em;
        }

        .metric-label {
            color: #6c7871;
            font-size: 0.8rem;
            font-weight: 600;
            margin-top: 0.4rem;
        }

        /* ====================================================
           CUSTOM TABLES
           ==================================================== */

        .custom-table-wrap {
            width: 100%;
            margin-top: 0.25rem;
            overflow-x: auto;
        }

        .custom-table {
            width: 100%;
            border-collapse: collapse;
            border-spacing: 0;
            background: #ffffff !important;
            border: 1px solid #ccd9d0;
        }

        .custom-table th {
            background: #edf4ef !important;
            color: #486050 !important;
            font-size: 0.82rem;
            font-weight: 700;
            text-align: left;
            padding: 0.78rem;
            border: 1px solid #ccd9d0;
            white-space: nowrap;
        }

        .custom-table td {
            background: #ffffff !important;
            color: #28342d !important;
            font-size: 0.9rem;
            font-weight: 500;
            padding: 0.78rem;
            border: 1px solid #d8e2db;
            white-space: nowrap;
        }

        .custom-table tr:hover td {
            background: #f7faf8 !important;
        }

        .table-emphasis {
            color: #365b40 !important;
            font-weight: 700 !important;
        }

        /* ====================================================
           NOTICE
           ==================================================== */

        .notice {
            border-left: 3px solid #8bab91;
            background: #f4f8f5;
            padding: 0.85rem 1rem;
            color: #536158;
            font-size: 0.92rem;
            line-height: 1.5;
            margin-top: 1rem;
        }

        /* ====================================================
           BUTTONS
           ==================================================== */

        .stDownloadButton > button,
        .stButton > button {
            border: 1px solid #9db8a3 !important;
            background: #eaf2ec !important;
            color: #35553e !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            font-weight: 700 !important;
            font-size: 0.9rem !important;
        }

        .stDownloadButton > button:hover,
        .stButton > button:hover {
            background: #dfebe1 !important;
            border-color: #75947d !important;
        }

        /* ====================================================
           IMAGES
           ==================================================== */

        [data-testid="stImage"] img {
            border-radius: 0 !important;
        }

        /* ====================================================
           ALERTS
           ==================================================== */

        [data-testid="stAlert"] {
            border-radius: 0 !important;
            border: 1px solid #d2dfd6 !important;
            background: #f4f8f5 !important;
            color: #526158 !important;
            font-size: 0.92rem !important;
        }

        /* ====================================================
           THEORY
           ==================================================== */

        .theory-copy {
            color: #59665f;
            font-size: 1rem;
            line-height: 1.65;
            max-width: 900px;
        }

        /* ====================================================
           MOBILE
           ==================================================== */

        @media (max-width: 800px) {

            .block-container {
                padding-left: 1.2rem;
                padding-right: 1.2rem;
            }

            .project-title {
                font-size: 2.5rem;
            }

            .metrics-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .metric-item:nth-child(2) {
                border-right: none;
            }
        }

        </style>
        """
    )
)


# ============================================================
# HTML RENDER HELPER
# ============================================================

def render_html(html: str) -> None:
    """
    Render HTML directly using Streamlit's HTML renderer.
    This prevents custom HTML from being interpreted as
    Markdown code blocks.
    """
    st.html(dedent(html))


# ============================================================
# TABLE RENDERER
# ============================================================

def render_table(
    headers: list[str],
    rows: list[list[str]],
) -> None:
    """Render a clean white HTML table."""

    header_html = "".join(
        f"<th>{header}</th>"
        for header in headers
    )

    body_html = ""

    for row in rows:

        cells_html = ""

        for index, value in enumerate(row):

            if index == 0:
                cells_html += (
                    f'<td class="table-emphasis">{value}</td>'
                )
            else:
                cells_html += f"<td>{value}</td>"

        body_html += f"<tr>{cells_html}</tr>"

    render_html(
        f"""
        <div class="custom-table-wrap">
            <table class="custom-table">
                <thead>
                    <tr>
                        {header_html}
                    </tr>
                </thead>
                <tbody>
                    {body_html}
                </tbody>
            </table>
        </div>
        """
    )


# ============================================================
# IMAGE ANALYSIS
# ============================================================

@st.cache_data(show_spinner=False)
def analyze_uploaded_image(
    file_bytes: bytes,
) -> dict:
    """Load image and calculate entropy statistics."""

    image = load_image(
        file_bytes
    )

    grayscale = grayscale_array(
        image
    )

    analysis = analyze_image(
        grayscale
    )

    return {
        "image": image,
        "analysis": analysis,
        "file_size": len(file_bytes),
    }


# ============================================================
# HISTOGRAM
# ============================================================

def create_histogram_plot(
    histogram: np.ndarray,
):
    """Create grayscale pixel frequency histogram."""

    intensity = np.arange(256)

    fig, ax = plt.subplots(
        figsize=(7.0, 3.0)
    )

    ax.bar(
        intensity,
        histogram,
        width=1,
        color="#8daa94",
        edgecolor="none",
    )

    ax.set_title(
        "Pixel intensity distribution",
        fontsize=12,
        fontweight="bold",
        loc="left",
        pad=10,
    )

    ax.set_xlabel(
        "Intensity",
        fontsize=9,
    )

    ax.set_ylabel(
        "Frequency",
        fontsize=9,
    )

    ax.set_xlim(
        0,
        255,
    )

    ax.spines[
        "top"
    ].set_visible(False)

    ax.spines[
        "right"
    ].set_visible(False)

    ax.tick_params(
        labelsize=8
    )

    ax.grid(
        axis="y",
        alpha=0.15,
    )

    fig.tight_layout()

    return fig


# ============================================================
# PROBABILITY DISTRIBUTION
# ============================================================

def create_probability_plot(
    probabilities: np.ndarray,
):
    """Create grayscale probability distribution."""

    intensity = np.arange(256)

    fig, ax = plt.subplots(
        figsize=(7.0, 3.0)
    )

    ax.plot(
        intensity,
        probabilities,
        color="#66866e",
        linewidth=1.8,
    )

    ax.fill_between(
        intensity,
        probabilities,
        color="#dce9de",
        alpha=0.9,
    )

    ax.set_title(
        "Pixel probability distribution",
        fontsize=12,
        fontweight="bold",
        loc="left",
        pad=10,
    )

    ax.set_xlabel(
        "Intensity",
        fontsize=9,
    )

    ax.set_ylabel(
        "Probability",
        fontsize=9,
    )

    ax.set_xlim(
        0,
        255,
    )

    ax.spines[
        "top"
    ].set_visible(False)

    ax.spines[
        "right"
    ].set_visible(False)

    ax.tick_params(
        labelsize=8
    )

    ax.grid(
        axis="y",
        alpha=0.15,
    )

    fig.tight_layout()

    return fig


# ============================================================
# RGB ENTROPY GRAPH
# ============================================================

def create_entropy_bar_plot(
    channel_results: dict,
):
    """Create compact RGB entropy comparison."""

    channels = list(
        channel_results.keys()
    )

    values = [
        channel_results[channel][
            "entropy"
        ]
        for channel in channels
    ]

    fig, ax = plt.subplots(
        figsize=(5.8, 2.8)
    )

    ax.bar(
        channels,
        values,
        width=0.42,
        color="#8daa94",
    )

    ax.set_title(
        "Entropy by colour channel",
        fontsize=12,
        fontweight="bold",
        loc="left",
        pad=10,
    )

    ax.set_ylabel(
        "Bits / pixel",
        fontsize=9,
    )

    ax.set_ylim(
        0,
        8,
    )

    ax.spines[
        "top"
    ].set_visible(False)

    ax.spines[
        "right"
    ].set_visible(False)

    ax.tick_params(
        labelsize=9
    )

    ax.grid(
        axis="y",
        alpha=0.15,
    )

    for index, value in enumerate(
        values
    ):

        ax.text(
            index,
            value + 0.12,
            f"{value:.3f}",
            ha="center",
            fontsize=9,
            fontweight="600",
            color="#405148",
        )

    fig.tight_layout()

    return fig


# ============================================================
# HEADER
# ============================================================

render_html(
    """
    <div class="project-label">
        Information Theory Mini Project
    </div>

    <div class="project-title">
        Image Entropy Analyzer
    </div>

    <div class="project-subtitle">
        Measure the statistical information contained in digital images using Shannon entropy.
    </div>

    <div class="project-how">
        <span>How it works:</span>
        image → pixel distribution → probability → entropy → redundancy
    </div>
    """
)


# ============================================================
# TABS
# ============================================================

analysis_tab, comparison_tab, theory_tab = st.tabs(
    [
        "Image analysis",
        "Comparison",
        "Theory",
    ]
)


# ============================================================
# IMAGE ANALYSIS TAB
# ============================================================

with analysis_tab:

    uploaded_file = st.file_uploader(
        "Upload image",
        type=list(
            SUPPORTED_FORMATS
        ),
        help=(
            "JPG, JPEG, PNG, WEBP, BMP or TIFF"
        ),
    )

    if uploaded_file is None:

        render_html(
            """
            <div class="rule"></div>

            <div class="section-title">
                Start with an image
            </div>

            <div class="body-copy">
                Upload an image to study its pixel distribution and
                calculate Shannon entropy, redundancy, and
                intensity-level statistics.
            </div>
            """
        )

    else:

        file_bytes = uploaded_file.getvalue()

        try:

            results = analyze_uploaded_image(
                file_bytes
            )

            image = results["image"]
            analysis = results["analysis"]

            grayscale_image = (
                convert_to_grayscale(
                    image
                )
            )

            # ----------------------------------------------------
            # INPUT
            # ----------------------------------------------------

            render_html(
                """
                <div class="section-title">
                    Input
                </div>
                """
            )

            image_col1, image_col2 = st.columns(
                2,
                gap="large",
            )

            with image_col1:

                render_html(
                    """
                    <div class="small-label">
                        Original
                    </div>
                    """
                )

                st.image(
                    image,
                    use_container_width=True,
                )

            with image_col2:

                render_html(
                    """
                    <div class="small-label">
                        Grayscale
                    </div>
                    """
                )

                st.image(
                    grayscale_image,
                    use_container_width=True,
                )

            # ----------------------------------------------------
            # RESULTS
            # ----------------------------------------------------

            render_html(
                """
                <div class="section-title">
                    Results
                </div>
                """
            )

            render_html(
                f"""
                <div class="metrics-grid">

                    <div class="metric-item">
                        <div class="metric-number">
                            {analysis["entropy"]:.4f}
                        </div>
                        <div class="metric-label">
                            Entropy · bits/pixel
                        </div>
                    </div>

                    <div class="metric-item">
                        <div class="metric-number">
                            {analysis["redundancy"]:.2f}%
                        </div>
                        <div class="metric-label">
                            Redundancy
                        </div>
                    </div>

                    <div class="metric-item">
                        <div class="metric-number">
                            {analysis["unique_levels"]}
                        </div>
                        <div class="metric-label">
                            Unique intensity levels
                        </div>
                    </div>

                    <div class="metric-item">
                        <div class="metric-number">
                            {analysis["maximum_entropy"]:.0f}
                        </div>
                        <div class="metric-label">
                            Maximum · bits/pixel
                        </div>
                    </div>

                </div>
                """
            )

            # ----------------------------------------------------
            # INTERPRETATION
            # ----------------------------------------------------

            normalized = (
                analysis["normalized_entropy"]
            )

            if normalized < 0.30:

                interpretation = (
                    "The pixel distribution is relatively concentrated, "
                    "resulting in lower entropy."
                )

            elif normalized < 0.70:

                interpretation = (
                    "The pixel distribution shows moderate variation, "
                    "resulting in moderate entropy."
                )

            else:

                interpretation = (
                    "The pixel distribution is spread across a wider "
                    "range of intensity values, resulting in higher entropy."
                )

            render_html(
                f"""
                <div class="notice">
                    {interpretation}
                </div>
                """
            )

            # ----------------------------------------------------
            # DISTRIBUTION GRAPHS
            # ----------------------------------------------------

            render_html(
                """
                <div class="section-title">
                    Pixel distribution
                </div>
                """
            )

            graph_col1, graph_col2 = st.columns(
                2,
                gap="large",
            )

            with graph_col1:

                histogram_fig = (
                    create_histogram_plot(
                        analysis["histogram"]
                    )
                )

                st.pyplot(
                    histogram_fig,
                    clear_figure=True,
                )

                plt.close(
                    histogram_fig
                )

            with graph_col2:

                probability_fig = (
                    create_probability_plot(
                        analysis["probabilities"]
                    )
                )

                st.pyplot(
                    probability_fig,
                    clear_figure=True,
                )

                plt.close(
                    probability_fig
                )

            # ----------------------------------------------------
            # COLOUR CHANNELS
            # ----------------------------------------------------

            render_html(
                """
                <div class="section-title">
                    Colour channels
                </div>
                """
            )

            channel_arrays = (
                rgb_channel_arrays(
                    image
                )
            )

            channel_results = {}

            for (
                channel_name,
                channel_array,
            ) in channel_arrays.items():

                channel_results[
                    channel_name
                ] = analyze_image(
                    channel_array
                )

            channel_rows = []

            for channel in channel_results:

                channel_rows.append(
                    [
                        channel,
                        (
                            f'{channel_results[channel]["entropy"]:.4f}'
                        ),
                        (
                            f'{channel_results[channel]["redundancy"]:.2f}%'
                        ),
                        (
                            f'{channel_results[channel]["unique_levels"]}'
                        ),
                    ]
                )

            render_table(
                headers=[
                    "Channel",
                    "Entropy (bits/pixel)",
                    "Redundancy (%)",
                    "Unique levels",
                ],
                rows=channel_rows,
            )

            # Compact chart centered on page
            chart_left, chart_center, chart_right = st.columns(
                [1, 2, 1]
            )

            with chart_center:

                channel_fig = (
                    create_entropy_bar_plot(
                        channel_results
                    )
                )

                st.pyplot(
                    channel_fig,
                    clear_figure=True,
                )

                plt.close(
                    channel_fig
                )

            # ----------------------------------------------------
            # IMAGE METADATA
            # ----------------------------------------------------

            render_html(
                """
                <div class="section-title">
                    Image metadata
                </div>
                """
            )

            width, height = image.size

            if "." in uploaded_file.name:

                extension = (
                    uploaded_file.name
                    .rsplit(
                        ".",
                        1,
                    )[-1]
                    .upper()
                )

            else:

                extension = "Unknown"

            metadata_rows = [
                [
                    "Format",
                    extension,
                ],
                [
                    "Colour mode",
                    image.mode,
                ],
                [
                    "Width",
                    f"{width} px",
                ],
                [
                    "Height",
                    f"{height} px",
                ],
                [
                    "Total pixels",
                    f"{width * height:,}",
                ],
                [
                    "File size",
                    format_file_size(
                        len(file_bytes)
                    ),
                ],
            ]

            render_table(
                headers=[
                    "Property",
                    "Value",
                ],
                rows=metadata_rows,
            )

            # ----------------------------------------------------
            # EXPORT
            # ----------------------------------------------------

            render_html(
                """
                <div class="section-title">
                    Export
                </div>
                """
            )

            export_dataframe = pd.DataFrame(
                [
                    {
                        "Filename": uploaded_file.name,
                        "Width": width,
                        "Height": height,
                        "Total Pixels": width * height,
                        "Entropy (bits/pixel)": round(
                            analysis["entropy"],
                            6,
                        ),
                        "Maximum Entropy": round(
                            analysis["maximum_entropy"],
                            6,
                        ),
                        "Normalized Entropy": round(
                            analysis["normalized_entropy"],
                            6,
                        ),
                        "Redundancy (%)": round(
                            analysis["redundancy"],
                            4,
                        ),
                        "Unique Intensity Levels": (
                            analysis[
                                "unique_levels"
                            ]
                        ),
                    }
                ]
            )

            csv_data = (
                export_dataframe
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8"
                )
            )

            st.download_button(
                "Download analysis CSV",
                data=csv_data,
                file_name=(
                    "image_entropy_analysis.csv"
                ),
                mime="text/csv",
            )

        except Exception as error:

            st.error(
                f"Analysis failed: {error}"
            )


# ============================================================
# COMPARISON TAB
# ============================================================

with comparison_tab:

    render_html(
        """
        <div class="section-title">
            Compare images
        </div>

        <div class="body-copy">
            Compare entropy and redundancy across multiple images
            using the same analysis method.
        </div>
        """
    )

    comparison_files = st.file_uploader(
        "Upload images",
        type=list(
            SUPPORTED_FORMATS
        ),
        accept_multiple_files=True,
        help="Select at least two images.",
        key="comparison_uploader",
    )

    if len(comparison_files) < 2:

        render_html(
            """
            <div class="notice">
                Upload at least two images to generate a comparison.
            </div>
            """
        )

    else:

        comparison_results = []

        progress = st.progress(
            0,
            text="Analyzing images...",
        )

        total_files = len(
            comparison_files
        )

        for index, file in enumerate(
            comparison_files
        ):

            try:

                file_bytes = (
                    file.getvalue()
                )

                results = (
                    analyze_uploaded_image(
                        file_bytes
                    )
                )

                analysis = (
                    results["analysis"]
                )

                comparison_results.append(
                    {
                        "Image": file.name,
                        "Entropy": (
                            analysis[
                                "entropy"
                            ]
                        ),
                        "Redundancy": (
                            analysis[
                                "redundancy"
                            ]
                        ),
                        "Unique levels": (
                            analysis[
                                "unique_levels"
                            ]
                        ),
                    }
                )

            except Exception as error:

                st.warning(
                    f"Skipped {file.name}: {error}"
                )

            progress.progress(
                (index + 1) / total_files,
                text=(
                    f"Analyzing "
                    f"{index + 1}/{total_files}"
                ),
            )

        progress.empty()

        if comparison_results:

            # ----------------------------------------------------
            # TABLE
            # ----------------------------------------------------

            comparison_rows = []

            for result in (
                comparison_results
            ):

                comparison_rows.append(
                    [
                        result["Image"],
                        (
                            f'{result["Entropy"]:.4f}'
                        ),
                        (
                            f'{result["Redundancy"]:.2f}%'
                        ),
                        (
                            f'{result["Unique levels"]}'
                        ),
                    ]
                )

            render_table(
                headers=[
                    "Image",
                    "Entropy (bits/pixel)",
                    "Redundancy (%)",
                    "Unique levels",
                ],
                rows=comparison_rows,
            )

            # ----------------------------------------------------
            # COMPARISON GRAPH
            # ----------------------------------------------------

            render_html(
                """
                <div class="section-title">
                    Entropy comparison
                </div>
                """
            )

            dataframe = pd.DataFrame(
                comparison_results
            )

            chart_left, chart_center, chart_right = st.columns(
                [1, 3, 1]
            )

            with chart_center:

                fig, ax = plt.subplots(
                    figsize=(7.5, 3.2)
                )

                ax.bar(
                    dataframe["Image"],
                    dataframe["Entropy"],
                    color="#8daa94",
                    width=0.45,
                )

                ax.set_ylabel(
                    "Bits / pixel",
                    fontsize=9,
                )

                ax.set_title(
                    "Entropy across images",
                    fontsize=12,
                    fontweight="bold",
                    loc="left",
                    pad=10,
                )

                ax.spines[
                    "top"
                ].set_visible(False)

                ax.spines[
                    "right"
                ].set_visible(False)

                ax.tick_params(
                    labelsize=8
                )

                ax.grid(
                    axis="y",
                    alpha=0.15,
                )

                plt.xticks(
                    rotation=20,
                    ha="right",
                )

                fig.tight_layout()

                st.pyplot(
                    fig,
                    clear_figure=True,
                )

                plt.close(
                    fig
                )

            # ----------------------------------------------------
            # EXPORT
            # ----------------------------------------------------

            export_dataframe = pd.DataFrame(
                {
                    "Image": [
                        result["Image"]
                        for result
                        in comparison_results
                    ],
                    "Entropy (bits/pixel)": [
                        round(
                            result["Entropy"],
                            6,
                        )
                        for result
                        in comparison_results
                    ],
                    "Redundancy (%)": [
                        round(
                            result["Redundancy"],
                            4,
                        )
                        for result
                        in comparison_results
                    ],
                    "Unique levels": [
                        result[
                            "Unique levels"
                        ]
                        for result
                        in comparison_results
                    ],
                }
            )

            comparison_csv = (
                export_dataframe
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8"
                )
            )

            st.download_button(
                "Download comparison CSV",
                data=comparison_csv,
                file_name=(
                    "image_entropy_comparison.csv"
                ),
                mime="text/csv",
            )


# ============================================================
# THEORY TAB
# ============================================================

with theory_tab:

    render_html(
        """
        <div class="section-title">
            Shannon entropy
        </div>

        <div class="theory-copy">
            Shannon entropy measures the average uncertainty in a
            probability distribution. For an image, the source is
            the distribution of grayscale pixel intensities.
        </div>
        """
    )

    st.latex(
        r"H(X)=-\sum_x p(x)\log_2 p(x)"
    )

    render_html(
        """
        <div class="section-title">
            Maximum entropy
        </div>

        <div class="theory-copy">
            An 8-bit grayscale image has 256 possible intensity values.
        </div>
        """
    )

    st.latex(
        r"H_{\max}=\log_2(256)=8\ \text{bits/pixel}"
    )

    render_html(
        """
        <div class="section-title">
            Normalized entropy
        </div>

        <div class="theory-copy">
            Normalized entropy expresses the measured entropy
            relative to the theoretical maximum.
        </div>
        """
    )

    st.latex(
        r"H_{\text{norm}}=\frac{H}{H_{\max}}"
    )

    render_html(
        """
        <div class="section-title">
            Redundancy
        </div>

        <div class="theory-copy">
            Redundancy represents the portion of the theoretical
            entropy capacity that is not utilized.
        </div>
        """
    )

    st.latex(
        r"R=\left(1-\frac{H}{H_{\max}}\right)\times100\%"
    )

    render_html(
        """
        <div class="section-title">
            Interpretation
        </div>

        <div class="theory-copy">
            A concentrated pixel distribution produces lower entropy,
            while a more widely distributed intensity pattern produces
            higher entropy. Entropy describes statistical information,
            not image quality.
        </div>
        """
    )