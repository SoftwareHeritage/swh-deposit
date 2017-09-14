from setuptools import setup


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
    packages=['swh.deposit',
              'swh.deposit.api',
              'swh.deposit.fixtures',
              'swh.deposit.migrations',
              'swh.deposit.settings',
              'swh.deposit.templates',
              'swh.deposit.templates.deposit',
              'swh.deposit.tests'],
    scripts=[],   # scripts to package
    install_requires=parse_requirements(),
    setup_requires=['vcversioner'],
    vcversioner={},
    include_package_data=True,
)
