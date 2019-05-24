import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="experiment_manager",
    version="0.0.1",
    author="Victor Ruelle",
    author_email="ruelle.victor@gmail.com",
    description="A thoughtless and all-round experiment manager for Python",
    long_description=long_description,
    license='MIT',
    long_description_content_type="text/markdown",
    url="https://github.com/victorruelle/ExperimentManager",
    packages=setuptools.find_packages(),
    install_requires=[
          'tensorflow',
          'keras',
          'superjson',
          'wrapt',
          'matplotlib',
          'numpy'
      ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: MIT License",
        "Experiment :: Manager :: OS Independent",
    ],
)
