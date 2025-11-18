from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="s3bridge-mw",
    version="1.0.0",
    author="Universal S3 Team",
    description="Account-agnostic credential service for secure S3 access with Midway authentication",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "boto3>=1.26.0",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "s3bridge-mw=s3bridge_mw.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["templates/*.yaml", "lambda_functions/*.py"],
    },
)