What is Packman?
================
Packman is a basic package manager which aims to provide a unified way to manage modifications for games which do not provide adequate management themselves. Such games include Kerbal Space Program, RimWorld and Emergency 5.

What isn't Packman?
===================
Packman is not a dependency management system. Although it would be nice to automatically install dependencies and ensure cross-compatibility, as mods do not have standardised manifests à la package.json, this would require a parallel database of mod dependencies be created and continuously maintained.

This would be a lot of work, introduce consistency issues where said database does not agree with the reality, creates the expectation that installing 100 mods should *just work* and just generally wouldn't be worth it as mod dependency trees tend to be very small anyway.

Quick start
===========
1. Install Python 3.9.1: https://www.python.org/downloads/release/python-391/
2. Install Poetry: pip install poetry
3. On Windows, install Make: http://gnuwin32.sourceforge.net/packages/make.htm
4. Start Packman: make cli or make gui

**Note:** At some point, it will be simpler than this - probably a compiled binary with an installer - but **it is not yet intended for general use**.

Settings
========
Currently, Packman settings are configured using environment variables; see packman/config.py.

At some point, this will change to be a configuration file in a more user-friendly format.

Configuring new mods
====================
Currently, mod configurations exist in the form of YAML files in the configs folder.

The schema for mod configurations can be found at docs/schemas/package_definition.json.

Contributing
============
All contributions are welcomed with open arms.

See the docs to get started (TODO).
