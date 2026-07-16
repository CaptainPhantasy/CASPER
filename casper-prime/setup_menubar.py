"""
Setup script for CASPER Prime Menu Bar App
"""

from setuptools import setup

APP = ['CasperMenuBar.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'iconfile': None,  # We'll use emoji icon
    'plist': {
        'CFBundleName': 'CASPER Prime',
        'CFBundleDisplayName': 'CASPER Prime',
        'CFBundleIdentifier': 'com.legacyai.casper-prime',
        'CFBundleVersion': "0.1.0",
        'CFBundleShortVersionString': "0.1.0",
        'NSHumanReadableCopyright': 'Legacy AI © 2024',
        'LSUIElement': True,  # Hide from dock, show only in menu bar
        'NSHighResolutionCapable': True,
    },
    'packages': ['rumps', 'requests'],
}

setup(
    name='CASPER Prime',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
