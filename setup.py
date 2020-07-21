from setuptools import setup, find_packages
from os import path


project_directory = path.abspath(path.dirname(__file__))


def load_from(file_name):
    with open(path.join(project_directory, file_name), encoding="utf-8") as f:
        return f.read()


setup(
    name="panamap",
    version=load_from("panamap/panamap.version").strip(),
    description="Python object mapper",
    long_description=load_from("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/kirillsulim/panamap",
    author="Kirill Sulim",
    author_email="kirillsulim@gmail.com",
    license="MIT",
    packages=find_packages(include=["panamap",]),
    package_data={"panamap": ["panamap.version",]},
    test_suite="tests",
    install_requires=["typing_inspect",],
    classifiers=["Development Status :: 4 - Beta", "License :: OSI Approved :: MIT License",],
    keywords="object mapper",
)
