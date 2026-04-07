from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="az-ai-data-migrator",
    version="0.1.0",
    author="Azure Data Migration Team",
    description="LLM-powered CLI tool for migrating unstructured data to Azure Blob Storage and Cosmos DB",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "anthropic>=0.38.0",
        "azure-cosmos>=4.6.1",
        "azure-storage-blob>=12.20.0",
        "azure-identity>=1.16.0",
        "click>=8.1.7",
        "pymongo>=4.6.1",
        "rich>=13.7.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.6.0",
    ],
    entry_points={
        "console_scripts": [
            "az-migrate=src.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
