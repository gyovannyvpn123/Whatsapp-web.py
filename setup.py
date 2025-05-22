#!/usr/bin/env python3
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="whatsapp-web-py",
    version="0.1.0",
    author="gyovannyvpn123",
    author_email="mdanut159@gmail.com",
    description="O bibliotecă Python pură pentru comunicarea cu WhatsApp Web",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gyovannyvpn123/Whatsapp-web.py",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Communications :: Chat",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
    install_requires=[
        "websockets",
        "cryptography",
        "protobuf",
        "pillow",
        "qrcode",
        "requests",
    ],
)
