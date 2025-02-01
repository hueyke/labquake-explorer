from setuptools import setup, find_packages

setup(
    name="labquake-explorer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "h5py",
        "matplotlib",
    ],
    entry_points={
        'console_scripts': [
            'labquake-explorer=labquake_explorer.main:main',
        ],
    },
    python_requires='>=3.7',
)