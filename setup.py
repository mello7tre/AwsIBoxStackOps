import setuptools

setuptools.setup(
    packages=[
        "iboxstacksops",
    ],
    package_data={},
    install_requires=[
        "boto3",
        "prettytable",
        "PyYAML>=5,==5.*",
        "tqdm",
    ],
    python_requires=">=3.7",
    scripts=[
        "scripts/ibox_stacksops.py",
    ],
    include_package_data=True,
)
