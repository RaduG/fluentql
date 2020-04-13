import os
from setuptools import setup


this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), "r") as f:
    long_description = f.read()


setup(
    name="fluentql",
    packages=["fluentql"],
    version="0.1.0",
    license="MIT",
    description="Lightweight and intuitive Python SQL query builder.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Radu Ghitescu",
    author_email="radu.ghitescu@gmail.com",
    url="https://github.com/RaduG/fluentql",
    classifiers=["Development Status :: 3 - Alpha", "Intended Audience :: Developers",],
    python_requires=">=3.6",
    zip_safe=False,
)
