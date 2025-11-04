#!/usr/bin/env python3
"""
Document Rip - AI-Powered Document to Markdown Pipeline

A cutting-edge, offline-first document to Markdown conversion system supporting 
PDF and Word documents with AI-powered vision validation and comprehensive quality assurance.
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="document-rip",
    version="2.0.0",  # Major version bump for AI vision integration
    author="Document Rip Team",
    author_email="team@documentrip.com",
    description="AI-Powered Document to Markdown Pipeline with Vision Validation",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/documentrip/document-rip",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=2.20.0",
        ],
        "vision": [
            "requests>=2.31.0",
            "pdf2image>=1.16.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pdfrip=src.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json"],
    },
    keywords=[
        "document-processing",
        "pdf-to-markdown",
        "word-to-markdown",
        "ai-vision",
        "quality-assurance",
        "automated-processing",
        "claude-vision",
        "document-conversion",
        "markdown",
        "pdf",
        "word",
        "ocr",
        "text-extraction",
    ],
    project_urls={
        "Bug Reports": "https://github.com/documentrip/document-rip/issues",
        "Source": "https://github.com/documentrip/document-rip",
        "Documentation": "https://github.com/documentrip/document-rip/blob/main/README.md",
    },
)
