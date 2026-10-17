#!/usr/bin/env python
"""
Setup script for AIQ-VeriClave.
This is kept for backward compatibility; primary config is in pyproject.toml.
"""

from setuptools import setup, find_packages

setup(
    name="aiq-vericlave",
    version="0.9.0",
    author="Satish Sura",
    author_email="satish@aiqi.in",
    description="AIQ-VeriClave: Evidence-first AI verification platform for silicon design",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/aiquanticinsights-commits/AIQ-VeriClave",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pyyaml>=6.0",
        "pydantic>=2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "ruff>=0.1.0",
            "mypy>=1.0",
            "pre-commit>=3.0",
        ],
        "test": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
        "dev-tools": [
            "ruff>=0.1.0",
            "mypy>=1.0",
            "pre-commit>=3.0",
        ],
        "docs": [
            "sphinx>=7.0",
            "sphinx-rtd-theme>=1.0",
            "myst-parser>=1.0",
        ],
        "ci": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "ruff>=0.1.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vericlave = router:main",
            "vericlave-eval = eval_harness:main",
            "vericlave-router = router:main",
            "vericlave-rewards = rewards:main",
            "vericlave-p0 = p0:main",
            "vericlave-p5 = p5_execute:main",
            "vericlave-rerun = p5_rerun:main",
            "vericlave-generate = generate:main",
            "vericlave-intent = intent:main",
            "vericlave-evidence = evidence:main",
            "vericlave-policy = policy:main",
            "vericlave-verify = eval_harness:main",
            "vericlave-signoff = simple_signoff:main",
            "vericlave-pilot = pilot_assist:main",
            "vericlave-pilot-human = pilot_human:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "Topic :: Software Development :: Quality Assurance",
    ],
    python_requires=">=3.10",
    zip_safe=False,
)
