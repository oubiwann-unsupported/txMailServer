from setuptools import setup

setup(name="txmailserver",
      version="imap4-0.1",
      description="This project provides a starter mail server written using Twisted.",
      keywords="twisted smtp imap pop email",
      url="https://launchpad.net/txmailserver",
      license="MIT / X / Expat License",
      packages=["txmailserver"],
      install_requires=[# -*- Extra requirements: -*-
                        "zope.interface",
                        "twisted"
                       ],
      test_suite="tests",
      tests_require=["nose"]
      )
