import setuptools
from pathlib import Path

source_root = Path(".")

with open(source_root / "README.md", "r") as fh:
    long_description = fh.read()

version = "0.2.1"

with open(source_root / "qam" / "version.py", "w") as fh:
    fh.writelines([
        f'__version__ = "{version}" \n '
    ])

setuptools.setup(
    name="quantitative-ablation-margin",
    version="0.2.1",
    author="Raluca M. Sandu",
    author_email="raluca-sandu@rwth-aachen.de",
    description="Calculation and visualization of ablation margins",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/artorg-unibe-ch/qam",
    packages=setuptools.find_packages(),
    install_requires = [
        "matplotlib>=3.3",
        "nibabel>=3.2",
        "numpy>=1.19",
        "openpyxl>=3.0.5",
        "pandas>=1.1",
        "scipy>=1.5",
        "xlrd>=1.2.0"
    ],
    extras_require = {
        '3d':  ["vtk>=9.0.1"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPL :: 3 ",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
