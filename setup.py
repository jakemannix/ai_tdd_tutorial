from setuptools import setup

setup(
    name="secure-services-tutorial",
    version="0.1.0",
    packages=[],  # No packages to install at root level
    install_requires=[],  # No base requirements
    extras_require={
        "dev": [
            "black>=23.7.0",
            "ruff>=0.0.286",
            "mypy>=1.5.1",
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
        ]
    },
    python_requires=">=3.10"
)

