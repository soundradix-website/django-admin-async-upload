import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-admin-async-upload',
    version='3.0.4',
    packages=['admin_async_upload'],
    include_package_data=True,
    package_data={
        'admin_async_upload': [
            'templates/admin_resumable/admin_file_input.html',
            'templates/admin_resumable/user_file_input.html',
            'static/admin_resumable/js/resumable.js',
        ]
    },
    license='MIT License',
    description='A Django app for the uploading of large files from the django admin site.',
    long_description=README,
    url='https://github.com/jonatron/django-admin-resumable-js',
    author='Alexey "DataGreed" Strelkov',
    author_email='datagreed@gmail.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=[
        'Django>=5.1',
    ],
    tests_require=[
        'pytest-django',
        'selenium',
        'pyvirtualdisplay',
    ]
)
