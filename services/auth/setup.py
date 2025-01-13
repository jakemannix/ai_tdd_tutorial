from setuptools import setup, find_namespace_packages

setup(
    name="auth-service",
    version="0.1.0",
    packages=find_namespace_packages(include=["auth_service*"]),
    package_dir={"": "src"},
)

