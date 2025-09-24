from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="casper-prime",
    version="0.1.0",
    author="CASPER Prime Team",
    description="Autonomous AI Development Platform with Agent Hierarchies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/casper-prime/casper-prime",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "anthropic>=0.7.0",
        "rich>=13.7.0",
        "asyncio>=3.11.0",
        "pydantic>=2.5.0",
        "websockets>=12.0",
        "aiofiles>=23.2.0",
        "python-multipart>=0.0.6",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "casper=core.cli:main",
        ],
    },
)