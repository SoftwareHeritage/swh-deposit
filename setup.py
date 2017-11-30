from setuptools import setup, find_packages


def parse_requirements():
    requirements = []
    for reqf in ('requirements.txt', 'requirements-swh.txt'):
        with open(reqf) as f:
            for line in f.readlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                requirements.append(line)
    return requirements


setup(
    name='swh.deposit',
    description='Software Heritage Deposit Server',
    author='Software Heritage developers',
    author_email='swh-devel@inria.fr',
    url='https://forge.softwareheritage.org/source/swh-deposit/',
    packages=find_packages(),
    scripts=[],   # scripts to package
    install_requires=parse_requirements(),
    extras_require={
        'loader': ['swh.loader.core >= 0.0.19',
                   'swh.scheduler >= 0.0.17',
                   'requests'],
    },
    setup_requires=['vcversioner'],
    vcversioner={},
    include_package_data=True,
)
