from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mdxmus2ndp",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="MDX MML to NDP MML Converter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/MDXMUS2NDP",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'mdx2ndp=mdx_converter_logic:main',
        ],
    },
)
