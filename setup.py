import setuptools

with open("README.md", "r") as f:
    long_desc = f.read()
    
setuptools.setup(
    name="pynuxmv",
    long_description=long_desc,
    version="0.1.0",
    author="Matteo Cavada",
    author_email="cvd00@insicuri.net",
    description="Transpile Python to nuXmv source code",
    url="https://github.com/mattyonweb/pynuxmv",
    packages=["pynuxmv"],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'pynuXmv = pynuxmv.cli:clio',
        ],
    },
    extras_require={
        "Pretty printing":  ["astpretty"],
    },
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Other",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Testing"
    ],
)
