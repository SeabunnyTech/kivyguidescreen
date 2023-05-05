try:
    from setuptools import setup, find_packages

except ImportError:
    from distutils.core import setup

setup(name='kivyguidescreen',
      version='0.1',
      description='a custom screen / screenmanager set that helps building basic apps',
      url='',
      author='Cloud',
      author_email='cloud@seabunny.tech',
      license='MIT',
      packages=['kivyguidescreen', 'kivyguidescreen.screens', 'kivyguidescreen.screensplus', 'kivyguidescreen.widgets', 'kivyguidescreen.utils'],
      install_requires=[
          'kivy'
      ],
      include_package_data=True,
      zip_safe=False)
