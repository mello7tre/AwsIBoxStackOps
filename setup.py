import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="iboxstacksops",
    version="0.4.8",
    author="Mello",
    author_email="mello+python@ankot.org",
    description="AWS Infrastructure in a Box - Stacks management program",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mello7tre/AwsIBoxStackOps",
    packages=["iboxstacksops",],
    package_data={},
    install_requires=["boto3", "prettytable", "PyYAML>=5,==5.*",],
    extras_require={"extra": ["slackclient"],},
    python_requires=">=3.7",
    scripts=["scripts/ibox_stacksops.py",],
    license="OSI Approved :: Open Software License 3.0 (OSL-3.0)",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Open Software License 3.0 (OSL-3.0)",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
)
