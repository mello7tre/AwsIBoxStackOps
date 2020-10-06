import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="iboxstacksops",
    version="0.2.7",
    author="Mello",
    author_email="mello+python@ankot.org",
    description="AWS Infrastructure in a Box - Stacks management program",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mello7tre/AwsIBoxStackOps",
    packages=[
        'iboxstacksops',
    ],
    package_data={},
    install_requires=[
        'boto3',
        'prettytable',
        'slackclient',
        'PyYAML>=5,==5.*',
    ],
    python_requires='>=3.7',
    scripts=[
        'scripts/ibox_stacksops.py',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
)
