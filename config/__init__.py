"""
SkillScope project package.

Django expects the MySQL driver to be importable as "MySQLdb". The usual
driver, mysqlclient, needs a C compiler to build on Windows. PyMySQL is pure
Python, installs anywhere, and can register itself under that name -- which is
what the two lines below do.

This has to happen before Django loads the database engine. This file is the
first thing Django imports from the project, so this is the right place for it.
"""

import pymysql

pymysql.install_as_MySQLdb()
