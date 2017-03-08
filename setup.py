from setuptools import setup

setup(name='caselink',
      version='0.1',
      description='Caselink API warpper for Python',
      url='http://github.com/ryncsn/caselink-python',
      author='Kairui Song',
      author_email='kasong@redhat.com',
      packages=['caselink'],
      package_data={'caselink': ['caselink-python.cfg']},
      zip_safe=False)

