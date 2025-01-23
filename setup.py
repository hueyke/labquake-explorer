from setuptools import setup, find_packages

setup(
    name="event-explorer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "h5py",
        "matplotlib",
    ],
    entry_points={
        'console_scripts': [
            'event-explorer=event_explorer.main:main',
        ],
    },
    python_requires='>=3.7',
)