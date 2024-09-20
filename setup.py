# setup.py

from setuptools import setup, find_packages

setup(
    name='django-payments-razorpay',
    version='0.1.0',
    description='Razorpay payment provider for django-payments',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/django-payments-razorpay',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'django-payments>=0.14.0',
        'razorpay>=1.3.0',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.2',  # or your Django version
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',  # Choose your license
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
)
