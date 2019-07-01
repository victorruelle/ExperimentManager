import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ExperimentManager",
    version="0.0.5.4",
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
          'numpy',
          'pydot',
          'graphviz'
      ]
)
