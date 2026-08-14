"""Custom Scrapy commands (optional).

Register project-specific ``scrapy`` sub-commands here. Each command is a
class implementing Scrapy's ``BaseCommand`` interface; the package is
auto-discovered because ``COMMANDS_MODULE`` can point at it.

Example:
    from scrapy.commands import BaseCommand

    class CheckConfig(BaseCommand):
        def run(self, args, opts):
            ...
"""

# To enable: set in settings/base.py:
#   COMMANDS_MODULE = "crawler.commands"
