# Image Entropy Analyzer

An interactive Information Theory project that analyzes the
information content of digital images using Shannon entropy.

## Objective

To study how the statistical distribution of image pixel
intensities affects entropy, redundancy, and information content.

## Features

- Shannon entropy calculation
- Maximum theoretical entropy
- Normalized entropy
- Redundancy calculation
- Pixel intensity histogram
- Pixel probability distribution
- RGB channel entropy analysis
- Multiple-image comparison
- CSV result export
- Interactive Streamlit interface

## Information Theory Concepts

### Shannon Entropy

H(X) = -Σ p(x) log₂ p(x)

### Maximum Entropy

For an 8-bit grayscale image:

Hmax = log₂(256) = 8 bits/pixel

### Normalized Entropy

Normalized Entropy = H / Hmax

### Redundancy

Redundancy = (1 - H/Hmax) × 100%

## Technologies

- Python
- NumPy
- Pandas
- Matplotlib
- Pillow
- Streamlit

## Project Structure

image-entropy-analyzer/

├── app.py  
├── entropy.py  
├── image_utils.py  
├── requirements.txt  
└── README.md

## Installation

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Install the dependencies and start the application:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Presentation and reproducible experiments

- [Project presentation](documentation/Image_Entropy_Analyzer_Presentation.pptx):
  17 editable slides with speaker notes, genuine interface screenshots and measured results.
- [Experiment script](documentation/experiments.py): generates synthetic test images,
  measures them using the project's actual loading and entropy functions, and runs
  17 numerical and input-validation checks.
- [Measured results](documentation/experiment_results.csv) and
  [environment manifest](documentation/experiment_manifest.json): full-precision
  measurements, library versions, seed and source hashes for the experimental snapshot.

Run the experiments from the project root after installing the application dependencies:

```bash
python documentation/experiments.py
```

The script recreates its synthetic PNGs and charts under `documentation/assets/`.
Generated assets, PDFs and local document-authoring/review files are excluded from Git.
The recorded source hashes describe the files at measurement time; the README has
subsequently been expanded with these instructions. Rerunning the script records
the current source snapshot.

All four experimental images are synthetic, 256 x 256 pixels. The landscape is
procedurally generated, not a natural photograph. The noise seed is `20261020`.

| Synthetic image | Entropy (bits/pixel) | Normalized entropy | Redundancy (%) | Unique levels |
| --- | ---: | ---: | ---: | ---: |
| Constant | 0.000000 | 0.000000 | 100.000000 | 1 |
| Four levels | 2.000000 | 0.250000 | 75.000000 | 4 |
| Landscape | 6.517914 | 0.814739 | 18.526078 | 106 |
| Noise | 7.996772 | 0.999597 | 0.040346 | 256 |

The project's redundancy metric is a normalized entropy deficit relative to the
8-bit maximum. It is not a measured compression saving. The analysis uses marginal
intensity distributions and ignores pixel arrangement; entropy is not an image-quality
score. RGB channels are analyzed separately, without a joint colour model.
