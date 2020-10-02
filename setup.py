import os

from setuptools import setup

def package_data(pkg, roots):
    """Generic function to find package_data.
    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.
    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}

setup(
    name="eol_duplicate_xblock",
    version="0.2",
    author="Felipe Espinoza",
    author_email="felipe.espinoza.r@uchile.cl",
    description="Authentication backend for Chile uchileedxlogin",
    long_description="Authentication backend for Chile uchileedxlogin",
    url="https://eol.uchile.cl",
    packages=['eol_duplicate_xblock'],
    install_requires=["unidecode>=1.1.1"],
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "cms.djangoapp": ["eol_duplicate_xblock = eol_duplicate_xblock.apps:EolDuplicateXblockConfig"],
        "lms.djangoapp": ["eol_duplicate_xblock = eol_duplicate_xblock.apps:EolDuplicateXblockConfig"]
    },
    package_data=package_data("eol_duplicate_xblock", ["static", "public"]),
)
