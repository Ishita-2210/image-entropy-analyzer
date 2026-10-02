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