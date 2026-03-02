from setuptools import setup, find_packages

setup(
    name="incident-response-system",
    version="0.1.0",
    description="AI-Powered Incident Response System using AWS Strands Agents",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "boto3>=1.34.0",
        "aws-lambda-powertools>=2.31.0",
        "hypothesis>=6.92.0",
    ],
)
