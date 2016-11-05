from distutils.version import StrictVersion

__all__ = ['main', 'log', 'export']

__version__ = '6.2.4'
# PEP396

strict_version = StrictVersion(__version__)
