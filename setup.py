from setuptools import find_packages, setup

setup(
    name="cli_agent",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "typer[all]",
        "requests",
        "rich",
    ],
    entry_points="""
        [console_scripts]
        cli-agent=cli_agent.main:app
    """,
)
