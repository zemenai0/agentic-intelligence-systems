from setuptools import find_packages, setup


setup(
    name="agentic-intelligence-systems",
    version="0.1.0",
    description="Repository scaffold for building agentic intelligence systems.",
    python_requires=">=3.12.3",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
)
