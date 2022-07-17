from importlib.metadata import entry_points
from setuptools import setup, find_packages

setup(
    name="SurgUI",
    version="0.1.0",
    description="Surgical videos annotation software",
    url="https://github.com/bnamazi/SurgUI",
    author="Babak Namazi",
    author_email="bnamazi098@gmail.com",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Software Development :: Build Tools",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    packages=find_packages(),
    entry_points={"console_scripts": ["surgui = surgui.__main__:main"]},
)
